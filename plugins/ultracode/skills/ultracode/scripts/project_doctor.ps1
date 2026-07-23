<#
.SYNOPSIS
Validates an initialized UltraCode repository without modifying it.

.PARAMETER ProjectRoot
Repository root to inspect. Defaults to the current directory.

.PARAMETER Json
Emits the result as JSON.

.OUTPUTS
Exit 0 for PASSED, 2 for DRIFT, and 1 for FAILED.
#>
[CmdletBinding()]
param(
    [string]$ProjectRoot = '.',
    [switch]$Json
)

$ErrorActionPreference = 'Stop'

$script:doctorErrors = New-Object 'System.Collections.Generic.List[string]'
$script:doctorDrift = New-Object 'System.Collections.Generic.List[string]'
$script:doctorWarnings = New-Object 'System.Collections.Generic.List[string]'

$script:requiredTopLevel = @(
    'schema_version',
    'project',
    'control',
    'authority',
    'swarm',
    'adapters',
    'artifacts',
    'commands',
    'completion',
    'roles'
)
$script:commandKeys = @('install', 'format', 'lint', 'typecheck', 'test', 'build', 'run', 'health')
$script:evidenceStates = @('VERIFIED', 'INFERRED', 'UNKNOWN')
$script:modelPolicies = @('strongest-available', 'balanced-available', 'inherit')
$script:modelSelectorPattern = '^[a-z0-9][a-z0-9._-]{2,}\z'
$script:reasoningEfforts = @('low', 'medium', 'high', 'xhigh', 'max', 'ultra')
$script:statusPattern = '^\.ultracode/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$'
$script:contextPattern = '^\.agents/context/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*\.md$'
$script:rulePattern = '^\.agents/rules/[a-z0-9]+(?:-[a-z0-9]+)*\.md$'
$script:ruleScopePattern = '^(?!/)(?![A-Za-z]:)(?!~)(?!.*(?:^|/)\.{1,2}(?:/|$))[A-Za-z0-9._*?-]+(?:/[A-Za-z0-9._*?-]+)*\z'
$script:skillPattern = '^\.agents/skills/[a-z0-9]+(?:-[a-z0-9]+)*/SKILL\.md$'
$script:managedPathPattern = '^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$'
$script:managedStartPattern = '^<!-- ultracode:([a-z0-9]+(?:-[a-z0-9]+)*):start -->$'
$script:managedEndPattern = '^<!-- ultracode:([a-z0-9]+(?:-[a-z0-9]+)*):end -->$'
$script:anyManagedMarkerPattern = '<!-- ultracode:[a-z0-9]+(?:-[a-z0-9]+)*:(?:start|end) -->'
$script:kebabPattern = '^[a-z0-9]+(?:-[a-z0-9]+)*$'
$script:sha256Pattern = '^[0-9a-f]{64}$'
$script:sourceHashPattern = 'ultracode-source-sha256:\s*([0-9a-f]{64})'

function Add-DoctorError {
    param([string]$Message)
    [void]$script:doctorErrors.Add($Message)
}

function Add-DoctorDrift {
    param([string]$Message)
    [void]$script:doctorDrift.Add($Message)
}

function Add-DoctorWarning {
    param([string]$Message)
    [void]$script:doctorWarnings.Add($Message)
}

function Test-DoctorObject {
    param($Value)
    return $null -ne $Value -and $Value -isnot [System.Array] -and (
        $Value -is [System.Management.Automation.PSCustomObject] -or
        $Value -is [System.Collections.IDictionary]
    )
}

function Test-ObjectProperty {
    param($Object, [string]$Name)
    if (-not (Test-DoctorObject $Object)) {
        return $false
    }
    if ($Object -is [System.Collections.IDictionary]) {
        foreach ($key in $Object.Keys) {
            if ($key -is [string] -and [string]::Equals($key, $Name, [System.StringComparison]::Ordinal)) {
                return $true
            }
        }
        return $false
    }
    foreach ($property in $Object.PSObject.Properties) {
        if ([string]::Equals($property.Name, $Name, [System.StringComparison]::Ordinal)) {
            return $true
        }
    }
    return $false
}

function Get-ObjectProperty {
    param($Object, [string]$Name)
    if (-not (Test-DoctorObject $Object)) {
        return $null
    }
    $found = $false
    $value = $null
    if ($Object -is [System.Collections.IDictionary]) {
        foreach ($key in $Object.Keys) {
            if ($key -is [string] -and [string]::Equals($key, $Name, [System.StringComparison]::Ordinal)) {
                $value = $Object[$key]
                $found = $true
                break
            }
        }
    }
    else {
        foreach ($property in $Object.PSObject.Properties) {
            if ([string]::Equals($property.Name, $Name, [System.StringComparison]::Ordinal)) {
                $value = $property.Value
                $found = $true
                break
            }
        }
    }
    if (-not $found) {
        return $null
    }
    if ($value -is [System.Array]) {
        Write-Output -NoEnumerate $value
        return
    }
    return $value
}

function Read-DoctorJson {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Add-DoctorError "missing required file: $Path"
        return $null
    }
    try {
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        $decoder = [System.Text.UTF8Encoding]::new($false, $true)
        $value = $decoder.GetString($bytes) | ConvertFrom-Json
    }
    catch {
        Add-DoctorError "cannot read JSON $Path`: $($_.Exception.Message)"
        return $null
    }
    if (-not (Test-DoctorObject $value)) {
        Add-DoctorError "JSON root must be an object: $Path"
        return $null
    }
    return $value
}

function Read-DoctorUtf8 {
    param([string]$Path, [string]$Label)
    try {
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        $decoder = [System.Text.UTF8Encoding]::new($false, $true)
        return $decoder.GetString($bytes)
    }
    catch {
        Add-DoctorError "cannot read $Label`: $($_.Exception.Message)"
        return $null
    }
}

function Require-DoctorObject {
    param($Parent, [string]$Key)
    $value = Get-ObjectProperty $Parent $Key
    if (-not (Test-DoctorObject $value)) {
        Add-DoctorError "$Key must be an object"
        return [pscustomobject]@{}
    }
    return $value
}

function Get-DoctorStringList {
    param(
        $Value,
        [string]$Label,
        [int]$Minimum = 0,
        [string]$Pattern = ''
    )
    $result = New-Object 'System.Collections.Generic.List[string]'
    if ($Value -isnot [System.Array]) {
        Add-DoctorError "$Label must be an array"
        return $result.ToArray()
    }
    if ($Value.Count -lt $Minimum) {
        Add-DoctorError "$Label must contain at least $Minimum item(s)"
    }
    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
    for ($index = 0; $index -lt $Value.Count; $index++) {
        $item = $Value[$index]
        if ($item -isnot [string] -or [string]::IsNullOrEmpty($item)) {
            Add-DoctorError "${Label}[$index] must be a non-empty string"
            continue
        }
        if (-not [string]::IsNullOrEmpty($Pattern) -and -not (Test-DoctorRegex $item $Pattern)) {
            Add-DoctorError "${Label}[$index] has an invalid path: $item"
        }
        if (-not $seen.Add($item)) {
            Add-DoctorError "$Label contains a duplicate: $item"
        }
        [void]$result.Add($item)
    }
    return $result.ToArray()
}

function Test-DoctorPositiveInteger {
    param($Value)
    $integerTypes = @(
        [byte], [sbyte], [int16], [uint16], [int32], [uint32], [int64], [uint64]
    )
    foreach ($type in $integerTypes) {
        if ($Value -is $type) {
            return $Value -ge 1
        }
    }
    return $false
}

function Test-DoctorIntegerOne {
    param($Value)
    return (Test-DoctorPositiveInteger $Value) -and ([uint64]$Value -eq 1)
}

function Test-DoctorExactString {
    param($Value, [string]$Expected)
    return $Value -is [string] -and [string]::Equals(
        $Value,
        $Expected,
        [System.StringComparison]::Ordinal
    )
}

function Test-DoctorExactStringIn {
    param($Value, [string[]]$Allowed)
    if ($Value -isnot [string]) {
        return $false
    }
    foreach ($candidate in $Allowed) {
        if ([string]::Equals($Value, $candidate, [System.StringComparison]::Ordinal)) {
            return $true
        }
    }
    return $false
}

function Test-DoctorRegex {
    param($Value, [string]$Pattern)
    return $Value -is [string] -and [regex]::IsMatch(
        $Value,
        $Pattern,
        [System.Text.RegularExpressions.RegexOptions]::CultureInvariant
    )
}

function Format-DoctorPathList {
    param([string[]]$Values)
    $quoted = @($Values | ForEach-Object { "'$_'" })
    return '[' + ($quoted -join ', ') + ']'
}

function ConvertTo-DoctorLf {
    param([string]$Text)
    return $Text.Replace("`r`n", "`n").Replace("`r", "`n")
}

function Get-DoctorFrontmatter {
    param([string]$Text)
    $normalized = ConvertTo-DoctorLf $Text
    $match = [regex]::Match(
        $normalized,
        '\A---[ \t]*\n(?<front>.*?)\n---[ \t]*\n(?<body>[\s\S]*)\z',
        [System.Text.RegularExpressions.RegexOptions]::Singleline
    )
    if (-not $match.Success) {
        return $null
    }
    return [pscustomobject]@{
        Front = $match.Groups['front'].Value
        Body = $match.Groups['body'].Value
    }
}

function Get-DoctorYamlTopKeys {
    param([string]$Frontmatter)
    $keys = New-Object 'System.Collections.Generic.List[string]'
    foreach ($match in [regex]::Matches($Frontmatter, '(?m)^([A-Za-z][A-Za-z0-9_-]*):')) {
        [void]$keys.Add($match.Groups[1].Value)
    }
    return $keys.ToArray()
}

function Test-DoctorYamlTopKeys {
    param([string[]]$Actual, [string[]]$Expected, [string]$Label)
    $valid = $true
    $counts = New-Object 'System.Collections.Generic.Dictionary[string,int]' ([System.StringComparer]::Ordinal)
    foreach ($key in $Actual) {
        if ($counts.ContainsKey($key)) {
            $counts[$key]++
        }
        else {
            $counts.Add($key, 1)
        }
    }
    foreach ($key in $counts.Keys) {
        if ($counts[$key] -ne 1) {
            Add-DoctorError "$Label frontmatter contains duplicate key: $key"
            $valid = $false
        }
    }
    $actualUnique = @($counts.Keys | Sort-Object)
    $expectedSorted = @($Expected | Sort-Object)
    if (($actualUnique -join "`n") -cne ($expectedSorted -join "`n")) {
        Add-DoctorError "$Label frontmatter keys must be exactly: $($expectedSorted -join ', ')"
        $valid = $false
    }
    return $valid
}

function Get-DoctorYamlList {
    param([string]$Frontmatter, [string]$Key, [string]$Label)
    $items = New-Object 'System.Collections.Generic.List[string]'
    $normalized = ConvertTo-DoctorLf $Frontmatter
    $lines = @($normalized -split "`n")
    $keyIndexes = New-Object 'System.Collections.Generic.List[int]'
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if (Test-DoctorRegex $lines[$index] ('^' + [regex]::Escape($Key) + ':\s*$')) {
            [void]$keyIndexes.Add($index)
        }
    }
    if ($keyIndexes.Count -ne 1) {
        Add-DoctorError "$Label must be a simple non-empty YAML list"
        return [pscustomobject]@{ Valid = $false; Items = $items.ToArray() }
    }
    $valid = $true
    for ($index = $keyIndexes[0] + 1; $index -lt $lines.Count; $index++) {
        $line = $lines[$index]
        if (Test-DoctorRegex $line '^[A-Za-z][A-Za-z0-9_-]*:') {
            break
        }
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $itemMatch = [regex]::Match($line, '^[ \t]+-[ \t]+(\S(?:.*\S)?)\s*$')
        if (-not $itemMatch.Success) {
            Add-DoctorError "$Label must be a simple non-empty YAML list"
            $valid = $false
            continue
        }
        [void]$items.Add($itemMatch.Groups[1].Value)
    }
    if ($items.Count -eq 0) {
        Add-DoctorError "$Label must be a non-empty YAML list"
        $valid = $false
    }
    return [pscustomobject]@{ Valid = $valid; Items = $items.ToArray() }
}

function Test-DoctorYamlStructure {
    param([string]$Frontmatter, [string[]]$ListKeys, [string]$Label)
    $normalized = ConvertTo-DoctorLf $Frontmatter
    $currentList = $null
    $valid = $true
    foreach ($line in @($normalized -split "`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $keyMatch = [regex]::Match($line, '^([A-Za-z][A-Za-z0-9_-]*):')
        if ($keyMatch.Success) {
            $key = $keyMatch.Groups[1].Value
            $currentList = if ($ListKeys -ccontains $key) { $key } else { $null }
            continue
        }
        if ($null -ne $currentList -and (Test-DoctorRegex $line '^[ \t]+-[ \t]+\S(?:.*\S)?\s*$')) {
            continue
        }
        Add-DoctorError "$Label frontmatter contains unsupported content"
        $valid = $false
    }
    return $valid
}

function Test-DoctorExactBody {
    param([string]$Body, [string]$Expected, [string]$ErrorMessage)
    $actual = ConvertTo-DoctorLf $Body
    if ($actual.EndsWith("`n", [System.StringComparison]::Ordinal)) {
        $actual = $actual.Substring(0, $actual.Length - 1)
    }
    if ($actual -cne $Expected) {
        Add-DoctorError $ErrorMessage
        return $false
    }
    return $true
}

function ConvertTo-DoctorJsonString {
    param([string]$Value)
    return ConvertTo-Json -Compress -InputObject $Value
}

function Get-DoctorStrictFrontmatter {
    param([string]$Text, [string]$Label)
    $normalized = ConvertTo-DoctorLf $Text
    $match = [regex]::Match(
        $normalized,
        '\A---[ \t]*\n(?<front>.*?)\n---[ \t]*\n',
        [System.Text.RegularExpressions.RegexOptions]::Singleline
    )
    if (-not $match.Success) {
        Add-DoctorError "$Label lacks YAML frontmatter"
        return $null
    }
    $front = $match.Groups['front'].Value
    $keys = New-Object 'System.Collections.Generic.Dictionary[string,string]' ([System.StringComparer]::Ordinal)
    foreach ($line in @($front -split "`n")) {
        if ([string]::IsNullOrEmpty($line) -or [char]::IsWhiteSpace($line[0])) {
            continue
        }
        $keyMatch = [regex]::Match($line, '^([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*)$')
        if (-not $keyMatch.Success) {
            Add-DoctorError "$Label has unsupported YAML frontmatter syntax"
            return $null
        }
        $key = $keyMatch.Groups[1].Value
        $value = $keyMatch.Groups[2].Value
        if ($keys.ContainsKey($key)) {
            Add-DoctorError "$Label contains duplicate frontmatter key: $key"
        }
        else {
            $keys.Add($key, $value)
        }
    }
    $body = $normalized.Substring($match.Index + $match.Length).Trim()
    return [pscustomobject]@{ Front = $front; Body = $body; Keys = $keys }
}

function Get-DoctorJsonYamlList {
    param([string]$Frontmatter, [string]$Key, [string]$Label)
    $lines = @($Frontmatter -split "`n")
    $start = -1
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -ceq "${Key}:") {
            $start = $index
            break
        }
    }
    if ($start -lt 0) {
        Add-DoctorError "$Label.$Key must use a block list"
        return [pscustomobject]@{ Valid = $false; Values = @() }
    }
    $values = New-Object 'System.Collections.Generic.List[string]'
    for ($index = $start + 1; $index -lt $lines.Count; $index++) {
        $line = $lines[$index]
        if (-not [string]::IsNullOrEmpty($line) -and -not [char]::IsWhiteSpace($line[0])) {
            break
        }
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $item = [regex]::Match($line, '^[ \t]+-[ \t]+(.+)$')
        if (-not $item.Success) {
            Add-DoctorError "$Label.$Key contains unsupported list syntax"
            return [pscustomobject]@{ Valid = $false; Values = $values.ToArray() }
        }
        try {
            $value = $item.Groups[1].Value | ConvertFrom-Json
        }
        catch {
            Add-DoctorError "$Label.$Key entries must be JSON-quoted strings"
            return [pscustomobject]@{ Valid = $false; Values = $values.ToArray() }
        }
        if ($value -isnot [string] -or [string]::IsNullOrEmpty($value)) {
            Add-DoctorError "$Label.$Key entries must be non-empty strings"
            return [pscustomobject]@{ Valid = $false; Values = $values.ToArray() }
        }
        [void]$values.Add($value)
    }
    if ($values.Count -eq 0) {
        Add-DoctorError "$Label.$Key must contain at least one item"
        return [pscustomobject]@{ Valid = $false; Values = @() }
    }
    return [pscustomobject]@{ Valid = $true; Values = $values.ToArray() }
}

function Get-DoctorJsonYamlScalar {
    param([string]$Raw, [string]$Label)
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        Add-DoctorError "$Label must be a JSON-quoted YAML string"
        return [pscustomobject]@{ Valid = $false; Value = $null }
    }
    try {
        $value = $Raw | ConvertFrom-Json
    }
    catch {
        Add-DoctorError "$Label must be a JSON-quoted YAML string"
        return [pscustomobject]@{ Valid = $false; Value = $null }
    }
    if ($value -isnot [string] -or [string]::IsNullOrWhiteSpace($value)) {
        Add-DoctorError "$Label must be a non-empty string"
        return [pscustomobject]@{ Valid = $false; Value = $null }
    }
    return [pscustomobject]@{ Valid = $true; Value = $value }
}

function Test-DoctorCanonicalSkill {
    param([string]$Path, [string]$Label, [string]$SkillName)
    $text = Read-DoctorUtf8 $Path $Label
    if ($null -eq $text) {
        return [pscustomobject]@{ Valid = $false; Description = $null }
    }
    $frontmatter = Get-DoctorStrictFrontmatter $text $Label
    if ($null -eq $frontmatter) {
        return [pscustomobject]@{ Valid = $false; Description = $null }
    }
    $valid = $true
    $actualKeys = @($frontmatter.Keys.Keys | Sort-Object)
    if (($actualKeys -join "`n") -cne (@('description', 'name') -join "`n")) {
        Add-DoctorError "$Label frontmatter must contain exactly name and description"
        $valid = $false
    }
    if (-not $frontmatter.Keys.ContainsKey('name') -or $frontmatter.Keys['name'] -cne $SkillName) {
        Add-DoctorError "$Label name must match canonical skill name $SkillName"
        $valid = $false
    }
    $rawDescription = if ($frontmatter.Keys.ContainsKey('description')) { $frontmatter.Keys['description'] } else { '' }
    $descriptionResult = Get-DoctorJsonYamlScalar $rawDescription "$Label.description"
    if (-not $descriptionResult.Valid) {
        $valid = $false
    }
    else {
        $expectedFrontmatter = "name: $SkillName`ndescription: $(ConvertTo-DoctorJsonString $descriptionResult.Value)"
        if ($frontmatter.Front -cne $expectedFrontmatter) {
            Add-DoctorError "$Label frontmatter differs from the deterministic canonical skill format"
            $valid = $false
        }
    }
    if ([string]::IsNullOrWhiteSpace($frontmatter.Body)) {
        Add-DoctorError "$Label body must be non-empty"
        $valid = $false
    }
    return [pscustomobject]@{
        Valid = $valid
        Description = if ($descriptionResult.Valid) { [string]$descriptionResult.Value } else { $null }
    }
}

function Resolve-DoctorPath {
    param([string]$Root, $Raw, [string]$Label)
    if ($Raw -isnot [string] -or [string]::IsNullOrEmpty($Raw)) {
        Add-DoctorError "$Label must be a non-empty relative POSIX path"
        return $null
    }
    if ($Raw.Contains('\')) {
        Add-DoctorError "$Label must use POSIX separators: $Raw"
        return $null
    }

    $allSegments = @($Raw.Split('/'))
    if (
        [System.IO.Path]::IsPathRooted($Raw) -or
        (Test-DoctorRegex $Raw '^[A-Za-z]:') -or
        $Raw.StartsWith('~', [System.StringComparison]::Ordinal) -or
        $allSegments -contains '..' -or
        $allSegments -contains '.' -or
        $allSegments -contains ''
    ) {
        Add-DoctorError "$Label escapes the repository: $Raw"
        return $null
    }

    $segments = $allSegments
    $current = $Root
    foreach ($segment in $segments) {
        $child = $null
        if (Test-Path -LiteralPath $current -PathType Container) {
            try {
                $caseInsensitive = @(Get-ChildItem -Force -LiteralPath $current | Where-Object { $_.Name -ieq $segment })
            }
            catch {
                Add-DoctorError "cannot inspect path casing for $Label`: $($_.Exception.Message)"
                return $null
            }
            if ($caseInsensitive.Count -gt 0) {
                $exact = @($caseInsensitive | Where-Object { $_.Name -ceq $segment })
                if ($exact.Count -eq 0) {
                    Add-DoctorError "$Label uses non-portable path casing: $Raw"
                    return $null
                }
                $child = $exact[0]
            }
        }

        if ($null -ne $child) {
            if (($child.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                Add-DoctorError "$Label traverses a symlink, junction, or reparse point: $Raw"
                return $null
            }
            $current = $child.FullName
        }
        else {
            $current = Join-Path $current $segment
            if (Test-Path -LiteralPath $current) {
                try {
                    $item = Get-Item -Force -LiteralPath $current
                    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                        Add-DoctorError "$Label traverses a symlink, junction, or reparse point: $Raw"
                        return $null
                    }
                }
                catch {
                    Add-DoctorError "cannot inspect path for $Label`: $($_.Exception.Message)"
                    return $null
                }
            }
        }
    }

    try {
        $candidate = [System.IO.Path]::GetFullPath($current)
    }
    catch {
        Add-DoctorError "$Label is not a valid repository path: $Raw"
        return $null
    }
    $separator = [System.IO.Path]::DirectorySeparatorChar
    $prefix = $Root.TrimEnd($separator, [System.IO.Path]::AltDirectorySeparatorChar) + $separator
    if ($candidate -ne $Root -and -not $candidate.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        Add-DoctorError "$Label resolves outside the repository: $Raw"
        return $null
    }
    return $candidate
}

function Require-DoctorFile {
    param([string]$Root, [string]$Raw, [string]$Label)
    $path = Resolve-DoctorPath $Root $Raw $Label
    if ($null -ne $path -and -not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Add-DoctorError "missing required artifact: $Raw"
        return $null
    }
    return $path
}

function Get-DoctorBlockHash {
    param([string]$Text, [string]$Start, [string]$End, [string]$Label, [ref]$BlockText)
    $normalized = ConvertTo-DoctorLf $Text
    $startMatch = [regex]::Match($Start, $script:managedStartPattern)
    $endMatch = [regex]::Match($End, $script:managedEndPattern)
    if (-not $startMatch.Success -or -not $endMatch.Success -or $startMatch.Groups[1].Value -cne $endMatch.Groups[1].Value) {
        Add-DoctorError "$Label must use a matching UltraCode start/end marker pair"
        return $null
    }
    $startCount = [regex]::Matches($normalized, [regex]::Escape($Start)).Count
    $endCount = [regex]::Matches($normalized, [regex]::Escape($End)).Count
    if ($startCount -ne 1 -or $endCount -ne 1) {
        Add-DoctorError "$Label must contain exactly one start and end marker"
        return $null
    }
    $begin = $normalized.IndexOf($Start, [System.StringComparison]::Ordinal)
    $finish = $normalized.IndexOf($End, [System.StringComparison]::Ordinal)
    if ($finish -lt $begin) {
        Add-DoctorError "$Label has reversed managed markers"
        return $null
    }
    $block = $normalized.Substring($begin, $finish + $End.Length - $begin)
    $managedMarkers = [regex]::Matches($block, $script:anyManagedMarkerPattern)
    if (
        $managedMarkers.Count -ne 2 -or
        $managedMarkers[0].Value -cne $Start -or
        $managedMarkers[1].Value -cne $End
    ) {
        Add-DoctorError "$Label contains nested or unexpected UltraCode block markers"
        return $null
    }
    if ($null -ne $BlockText) {
        $BlockText.Value = $block
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = ([System.Text.UTF8Encoding]::new($false)).GetBytes($block)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
}

function Get-DoctorProjectionText {
    param([string]$Path, [string]$SourceHash, [string]$Label)
    $text = Read-DoctorUtf8 $Path $Label
    if ($null -eq $text) {
        return $null
    }
    $matches = [regex]::Matches($text, $script:sourceHashPattern)
    if ($matches.Count -ne 1) {
        Add-DoctorError "$Label must contain exactly one ultracode-source-sha256"
    }
    elseif ($matches[0].Groups[1].Value -cne $SourceHash) {
        Add-DoctorError "$Label source hash does not match its canonical reviewer"
    }
    return $text
}

function Test-DoctorCodexRoleProjection {
    param(
        [string]$Path,
        [string]$Label,
        [string]$SourceHash,
        [string]$RoleId,
        [string]$RolePurpose,
        [string]$RoleMode,
        [string]$CanonicalRaw
    )
    $text = Get-DoctorProjectionText $Path $SourceHash $Label
    if ($null -eq $text) {
        return
    }
    $marker = "# ultracode-canonical: $CanonicalRaw"
    $namePattern = '(?m)^name\s*=\s*"' + [regex]::Escape($RoleId) + '"\s*$'
    if (-not (Test-DoctorRegex $text $namePattern)) {
        Add-DoctorError "$Label name must match role id $RoleId"
    }
    $description = [regex]::Match($text, '(?m)^description\s*=\s*"((?:[^"\\]|\\.)+)"\s*$')
    if (-not $description.Success) {
        Add-DoctorError "$Label must define a non-empty description"
    }
    else {
        try {
            $decodedDescription = ('"' + $description.Groups[1].Value + '"') | ConvertFrom-Json
            if ($decodedDescription -cne $RolePurpose) {
                Add-DoctorError "$Label description must exactly match the configured role purpose"
            }
        }
        catch {
            Add-DoctorError "$Label description must exactly match the configured role purpose"
        }
    }
    $developer = [regex]::Match($text, '(?ms)^developer_instructions\s*=\s*"""(.*?)"""\s*$')
    if (-not $developer.Success -or [string]::IsNullOrWhiteSpace($developer.Groups[1].Value)) {
        Add-DoctorError "$Label must define non-empty developer_instructions"
    }
    else {
        $tick = [char]96
        $directive = "Read and follow the canonical reviewer at ${tick}${CanonicalRaw}${tick} completely before starting work."
        $expectedDeveloper = "`n${directive}`nReturn evidence and stay inside the assigned job boundary.`n"
        if ((ConvertTo-DoctorLf $developer.Groups[1].Value) -cne $expectedDeveloper) {
            Add-DoctorError "$Label developer_instructions differ from the deterministic role projection"
        }
    }
    $sandboxPattern = '(?m)^sandbox_mode\s*=\s*"' + [regex]::Escape($RoleMode) + '"\s*$'
    if (-not (Test-DoctorRegex $text $sandboxPattern)) {
        Add-DoctorError "$Label sandbox_mode must match role mode $RoleMode"
    }

    $normalized = (ConvertTo-DoctorLf $text).Trim()
    $sourceMarker = "# ultracode-source-sha256: $SourceHash"
    $tick = [char]96
    $directive = "Read and follow the canonical reviewer at ${tick}${CanonicalRaw}${tick} completely before starting work."
    $encodedPurpose = ConvertTo-DoctorJsonString $RolePurpose
    $expected = $marker + "`n" +
        $sourceMarker + "`n" +
        "name = `"$RoleId`"`n" +
        "description = $encodedPurpose`n" +
        "sandbox_mode = `"$RoleMode`"`n" +
        "developer_instructions = `"`"`"`n" +
        $directive + "`n" +
        'Return evidence and stay inside the assigned job boundary.' + "`n" +
        '"""'
    if ($normalized -cne $expected) {
        Add-DoctorError "$Label contains extra, duplicate, reordered, or ambiguous TOML content"
    }
}

function Test-DoctorClaudeRoleProjection {
    param(
        [string]$Path,
        [string]$Label,
        [string]$SourceHash,
        [string]$RoleId,
        [string]$RolePurpose,
        [string]$RoleMode,
        [string]$CanonicalRaw,
        [string[]]$RoleSkills
    )
    $text = Get-DoctorProjectionText $Path $SourceHash $Label
    if ($null -eq $text) {
        return
    }
    $frontmatter = Get-DoctorStrictFrontmatter $text $Label
    if ($null -eq $frontmatter) {
        return
    }
    $expectedKeys = @('name', 'description', 'permissionMode')
    if ($RoleSkills.Count -gt 0) {
        $expectedKeys += 'skills'
    }
    $actualKeys = @($frontmatter.Keys.Keys | Sort-Object)
    $expectedSorted = @($expectedKeys | Sort-Object)
    if (($actualKeys -join "`n") -cne ($expectedSorted -join "`n")) {
        Add-DoctorError "$Label frontmatter must contain exactly $(Format-DoctorPathList $expectedSorted)"
    }
    if (-not $frontmatter.Keys.ContainsKey('name') -or $frontmatter.Keys['name'] -cne $RoleId) {
        Add-DoctorError "$Label name must match role id $RoleId"
    }
    $rawDescription = if ($frontmatter.Keys.ContainsKey('description')) { $frontmatter.Keys['description'] } else { '' }
    $descriptionResult = Get-DoctorJsonYamlScalar $rawDescription "$Label.description"
    if ($descriptionResult.Valid -and $descriptionResult.Value -cne $RolePurpose) {
        Add-DoctorError "$Label.description must exactly match the configured role purpose"
    }
    $permissionMode = if (Test-DoctorExactString $RoleMode 'read-only') { 'plan' } else { 'default' }
    if (-not $frontmatter.Keys.ContainsKey('permissionMode') -or $frontmatter.Keys['permissionMode'] -cne $permissionMode) {
        Add-DoctorError "$Label permissionMode must be $permissionMode"
    }
    if ($RoleSkills.Count -gt 0) {
        $skillsResult = Get-DoctorJsonYamlList $frontmatter.Front 'skills' $Label
        if ($skillsResult.Valid) {
            $actualSkills = @($skillsResult.Values)
            if (($actualSkills -join "`n") -cne ($RoleSkills -join "`n")) {
                Add-DoctorError "$Label.skills must exactly match configured role skills"
            }
        }
    }

    $expectedFrontmatter = "name: $RoleId`n" +
        "description: $(ConvertTo-DoctorJsonString $RolePurpose)`n" +
        "permissionMode: $permissionMode"
    if ($RoleSkills.Count -gt 0) {
        $expectedFrontmatter += "`nskills:"
        foreach ($skill in $RoleSkills) {
            $expectedFrontmatter += "`n  - $(ConvertTo-DoctorJsonString $skill)"
        }
    }
    if ($frontmatter.Front -cne $expectedFrontmatter) {
        Add-DoctorError "$Label frontmatter differs from the deterministic role projection"
    }
    $marker = "<!-- ultracode-canonical: $CanonicalRaw -->"
    $sourceMarker = "<!-- ultracode-source-sha256: $SourceHash -->"
    $tick = [char]96
    $directive = "Read and follow the canonical reviewer at ${tick}${CanonicalRaw}${tick} completely before starting work."
    $expectedBody = $marker + "`n" + $sourceMarker + "`n`n" + $directive + "`n" + 'Return evidence and stay inside the assigned job boundary.'
    if ($frontmatter.Body -cne $expectedBody) {
        Add-DoctorError "$Label body differs from the deterministic canonical reviewer adapter"
    }
}

function Test-DoctorLocalStatusGit {
    param([string]$Root, [string]$StatusPath)
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($null -eq $git) {
        Add-DoctorWarning 'Git is unavailable; local status ignore state was not checked'
        return
    }

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        # Windows PowerShell 5.1 promotes redirected native stderr to ErrorRecord.
        # Keep the native exit code authoritative instead of terminating the doctor.
        $ErrorActionPreference = 'SilentlyContinue'
        $probeOutput = @(& $git.Source -C $Root rev-parse --show-toplevel 2>&1)
        $probeCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($probeCode -ne 0) {
        $probeText = ($probeOutput | ForEach-Object { $_.ToString() }) -join ' '
        if ($probeText.ToLowerInvariant().Contains('not a git repository')) {
            Add-DoctorWarning 'project is not a Git repository; local status needs no Git ignore rule'
        }
        else {
            Add-DoctorError "cannot verify Git state for local status: $probeText"
        }
        return
    }

    try {
        $ErrorActionPreference = 'SilentlyContinue'
        & $git.Source -C $Root ls-files --error-unmatch -- $StatusPath 2>$null | Out-Null
        $trackedCode = $LASTEXITCODE
        & $git.Source -C $Root check-ignore --quiet -- $StatusPath 2>$null | Out-Null
        $ignoredCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($trackedCode -eq 0) {
        Add-DoctorError "local status path is tracked by Git: $StatusPath"
    }
    if ($ignoredCode -ne 0) {
        Add-DoctorError "local status path is not ignored by Git: $StatusPath"
    }
}

function Test-DoctorConfig {
    param($Config, [string]$Root)

    $expectedManaged = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
    [void]$expectedManaged.Add('.ultracode/config.json')
    [void]$expectedManaged.Add('AGENTS.md')
    $statusPathRaw = $null

    foreach ($key in $script:requiredTopLevel) {
        if (-not (Test-ObjectProperty $Config $key)) {
            Add-DoctorError "config missing key: $key"
        }
    }
    if (-not (Test-DoctorIntegerOne (Get-ObjectProperty $Config 'schema_version'))) {
        Add-DoctorError 'config.schema_version must be 1'
    }

    $project = Require-DoctorObject $Config 'project'
    foreach ($key in @('name', 'mission')) {
        $value = Get-ObjectProperty $project $key
        if ($value -isnot [string] -or [string]::IsNullOrWhiteSpace($value)) {
            Add-DoctorError "project.$key must be a non-empty string"
        }
    }
    if (-not (Test-DoctorExactString (Get-ObjectProperty $project 'root') '.')) {
        Add-DoctorError "project.root must be '.'"
    }
    foreach ($key in @('stack', 'targets', 'non_goals')) {
        [void]@(Get-DoctorStringList (Get-ObjectProperty $project $key) "project.$key")
    }

    $control = Require-DoctorObject $Config 'control'
    if (-not (Test-DoctorExactStringIn (Get-ObjectProperty $control 'plan_gate') @('follow-repository', 'confirm-before-write', 'autonomous-within-authority'))) {
        Add-DoctorError 'control.plan_gate is invalid'
    }
    if (-not (Test-DoctorExactStringIn (Get-ObjectProperty $control 'updates') @('phase-and-barrier', 'phase-only', 'detailed'))) {
        Add-DoctorError 'control.updates is invalid'
    }
    if (-not (Test-DoctorExactStringIn (Get-ObjectProperty $control 'detail') @('compact', 'standard', 'detailed'))) {
        Add-DoctorError 'control.detail is invalid'
    }
    foreach ($key in @('show_agent_jobs', 'show_files', 'show_validation')) {
        if ((Get-ObjectProperty $control $key) -isnot [bool]) {
            Add-DoctorError "control.$key must be boolean"
        }
    }
    $persistence = Get-ObjectProperty $control 'persistent_status'
    if (-not (Test-DoctorExactStringIn $persistence @('conversation-only', 'local', 'tracked'))) {
        Add-DoctorError 'control.persistent_status is invalid'
    }
    $statusPathRaw = Get-ObjectProperty $control 'status_path'
    $resolvedStatusPath = Resolve-DoctorPath $Root $statusPathRaw 'control.status_path'
    if (-not (Test-DoctorRegex $statusPathRaw $script:statusPattern)) {
        Add-DoctorError 'control.status_path must be a portable path under .ultracode/'
    }
    if ((Test-DoctorExactString $persistence 'local') -and $null -ne $resolvedStatusPath -and $statusPathRaw -is [string]) {
        Test-DoctorLocalStatusGit $Root $statusPathRaw
    }

    $authority = Require-DoctorObject $Config 'authority'
    foreach ($key in @('git', 'external', 'destructive', 'dependencies', 'deployment')) {
        if (-not (Test-DoctorExactString (Get-ObjectProperty $authority $key) 'explicit-only')) {
            Add-DoctorError "authority.$key must be explicit-only"
        }
    }
    if (-not (Test-DoctorExactStringIn (Get-ObjectProperty $authority 'status_writes') @('change-tasks-only', 'explicit-per-task'))) {
        Add-DoctorError 'authority.status_writes is invalid'
    }

    $swarm = Require-DoctorObject $Config 'swarm'
    $expectedSwarm = [ordered]@{
        decomposition = 'data-driven'
        orthogonal_lenses = 'as-needed'
        verification = 'one-per-material-finding'
        synthesis_agents = 1
    }
    foreach ($key in $expectedSwarm.Keys) {
        $actual = Get-ObjectProperty $swarm $key
        $expected = $expectedSwarm[$key]
        if ($key -ceq 'synthesis_agents') {
            if (-not (Test-DoctorIntegerOne $actual)) {
                Add-DoctorError 'swarm.synthesis_agents must be 1'
            }
        }
        elseif (-not (Test-DoctorExactString $actual $expected)) {
            Add-DoctorError "swarm.$key must be '$expected'"
        }
    }
    if (Test-ObjectProperty $swarm 'max_total_agents') {
        Add-DoctorError 'swarm.max_total_agents is forbidden; use hard_safety_cap only'
    }
    $concurrency = Get-ObjectProperty $swarm 'concurrency'
    if (-not (Test-DoctorExactString $concurrency 'auto') -and -not (Test-DoctorPositiveInteger $concurrency)) {
        Add-DoctorError "swarm.concurrency must be 'auto' or a positive integer"
    }
    if (-not (Test-DoctorPositiveInteger (Get-ObjectProperty $swarm 'hard_safety_cap'))) {
        Add-DoctorError 'swarm.hard_safety_cap must be a positive integer'
    }
    $modelPolicy = Get-ObjectProperty $swarm 'model_policy'
    if (-not (Test-DoctorObject $modelPolicy)) {
        Add-DoctorError 'swarm.model_policy must be an object'
    }
    else {
        foreach ($key in @('lead', 'bounded_agents', 'verifiers')) {
            $selector = Get-ObjectProperty $modelPolicy $key
            if (-not (Test-DoctorExactStringIn $selector $script:modelPolicies) -and -not (Test-DoctorRegex $selector $script:modelSelectorPattern)) {
                Add-DoctorError "swarm.model_policy.$key is invalid"
            }
        }
        if (-not (Test-DoctorExactString (Get-ObjectProperty $modelPolicy 'fallback') 'inherit')) {
            Add-DoctorError 'swarm.model_policy.fallback must be inherit'
        }
    }
    $reasoningPolicy = Get-ObjectProperty $swarm 'reasoning_policy'
    if (-not (Test-DoctorObject $reasoningPolicy)) {
        Add-DoctorError 'swarm.reasoning_policy must be an object'
    }
    else {
        $requiredReasoningKeys = @(
            'mode',
            'bounded_default',
            'material_verifier_minimum',
            'critical_minimum',
            'maximum'
        )
        $actualReasoningKeys = @($reasoningPolicy.PSObject.Properties.Name)
        if ($reasoningPolicy -is [System.Collections.IDictionary]) {
            $actualReasoningKeys = @($reasoningPolicy.Keys)
        }
        $actualReasoningSet = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
        foreach ($key in $actualReasoningKeys) {
            if ($key -is [string]) { [void]$actualReasoningSet.Add($key) }
        }
        $requiredReasoningSet = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
        foreach ($key in $requiredReasoningKeys) { [void]$requiredReasoningSet.Add($key) }
        if (-not $actualReasoningSet.SetEquals($requiredReasoningSet)) {
            Add-DoctorError 'swarm.reasoning_policy must be an exact object'
        }
        if (-not (Test-DoctorExactString (Get-ObjectProperty $reasoningPolicy 'mode') 'objective-driven')) {
            Add-DoctorError 'swarm.reasoning_policy.mode must be objective-driven'
        }
        $reasoningIndexes = @{}
        foreach ($key in @('bounded_default', 'material_verifier_minimum', 'critical_minimum', 'maximum')) {
            $effort = Get-ObjectProperty $reasoningPolicy $key
            $effortIndex = if ($effort -is [string]) {
                [array]::IndexOf([string[]]$script:reasoningEfforts, [string]$effort)
            }
            else {
                -1
            }
            if ($effortIndex -lt 0) {
                Add-DoctorError "swarm.reasoning_policy.$key is invalid"
            }
            else {
                $reasoningIndexes[$key] = $effortIndex
            }
        }
        $highIndex = [array]::IndexOf([string[]]$script:reasoningEfforts, 'high')
        $xhighIndex = [array]::IndexOf([string[]]$script:reasoningEfforts, 'xhigh')
        if (
            $reasoningIndexes.ContainsKey('material_verifier_minimum') -and
            $reasoningIndexes['material_verifier_minimum'] -lt $highIndex
        ) {
            Add-DoctorError 'swarm.reasoning_policy.material_verifier_minimum must be at least high'
        }
        if (
            $reasoningIndexes.ContainsKey('critical_minimum') -and
            $reasoningIndexes['critical_minimum'] -lt $xhighIndex
        ) {
            Add-DoctorError 'swarm.reasoning_policy.critical_minimum must be at least xhigh'
        }
        if (
            $reasoningIndexes.ContainsKey('bounded_default') -and
            $reasoningIndexes.ContainsKey('material_verifier_minimum') -and
            $reasoningIndexes.ContainsKey('critical_minimum') -and
            $reasoningIndexes.ContainsKey('maximum') -and
            -not (
                $reasoningIndexes['bounded_default'] -le $reasoningIndexes['material_verifier_minimum'] -and
                $reasoningIndexes['material_verifier_minimum'] -le $reasoningIndexes['critical_minimum'] -and
                $reasoningIndexes['critical_minimum'] -le $reasoningIndexes['maximum']
            )
        ) {
            Add-DoctorError 'swarm.reasoning_policy efforts must be ordered through maximum'
        }
    }

    $adapters = Require-DoctorObject $Config 'adapters'
    foreach ($key in @('codex', 'claude')) {
        if ((Get-ObjectProperty $adapters $key) -isnot [bool]) {
            Add-DoctorError "adapters.$key must be boolean"
        }
    }
    $codexEnabled = (Get-ObjectProperty $adapters 'codex') -is [bool] -and (Get-ObjectProperty $adapters 'codex')
    $claudeEnabled = (Get-ObjectProperty $adapters 'claude') -is [bool] -and (Get-ObjectProperty $adapters 'claude')
    if (-not $codexEnabled -and -not $claudeEnabled) {
        Add-DoctorError 'at least one adapter must be enabled'
    }

    $agentsPath = Require-DoctorFile $Root 'AGENTS.md' 'AGENTS.md'
    $agentsText = if ($null -ne $agentsPath) { Read-DoctorUtf8 $agentsPath 'AGENTS.md' } else { $null }
    $agentsBlock = $null
    if ($null -ne $agentsText) {
        [void](Get-DoctorBlockHash $agentsText '<!-- ultracode:project:start -->' '<!-- ultracode:project:end -->' 'AGENTS.md' ([ref]$agentsBlock))
    }
    if ($null -ne $agentsBlock -and $agentsBlock.IndexOf('.ultracode/config.json', [System.StringComparison]::Ordinal) -lt 0) {
        Add-DoctorError 'AGENTS.md managed project block must route to .ultracode/config.json'
    }

    $artifacts = Require-DoctorObject $Config 'artifacts'
    $contexts = @(Get-DoctorStringList (Get-ObjectProperty $artifacts 'context') 'artifacts.context' 1 $script:contextPattern)
    $rules = @(Get-DoctorStringList (Get-ObjectProperty $artifacts 'rules') 'artifacts.rules' 0 $script:rulePattern)
    $rulePathsObject = Get-ObjectProperty $artifacts 'rule_paths'
    $rulePaths = @{}
    if (-not (Test-DoctorObject $rulePathsObject)) {
        Add-DoctorError 'artifacts.rule_paths must be an object'
    }
    else {
        $rulePathKeys = if ($rulePathsObject -is [System.Collections.IDictionary]) {
            @($rulePathsObject.Keys | ForEach-Object { [string]$_ } | Sort-Object)
        }
        else {
            @($rulePathsObject.PSObject.Properties.Name | Sort-Object)
        }
        $sortedRules = @($rules | Sort-Object)
        if (($rulePathKeys -join "`n") -cne ($sortedRules -join "`n")) {
            Add-DoctorError 'artifacts.rule_paths keys must exactly match artifacts.rules'
        }
        foreach ($raw in $rules) {
            $rulePaths[$raw] = @(
                Get-DoctorStringList (
                    Get-ObjectProperty $rulePathsObject $raw
                ) "artifacts.rule_paths['$raw']" 1 $script:ruleScopePattern
            )
        }
    }
    $skills = @(Get-DoctorStringList (Get-ObjectProperty $artifacts 'skills') 'artifacts.skills' 0 $script:skillPattern)
    $canonicalArtifacts = @($contexts) + @($rules) + @($skills)
    $canonicalFiles = New-Object 'System.Collections.Generic.Dictionary[string,string]' ([System.StringComparer]::Ordinal)
    for ($index = 0; $index -lt $canonicalArtifacts.Count; $index++) {
        $raw = $canonicalArtifacts[$index]
        $canonicalFile = Require-DoctorFile $Root $raw "artifacts[$index]"
        if ($null -ne $canonicalFile) {
            $canonicalFiles[$raw] = $canonicalFile
        }
        [void]$expectedManaged.Add($raw)
        if ($null -ne $agentsBlock -and $agentsBlock.IndexOf($raw, [System.StringComparison]::Ordinal) -lt 0) {
            Add-DoctorError "AGENTS.md does not route to canonical artifact: $raw"
        }
    }
    $canonicalSkillDescriptions = New-Object 'System.Collections.Generic.Dictionary[string,string]' ([System.StringComparer]::Ordinal)
    foreach ($raw in $skills) {
        if (-not $canonicalFiles.ContainsKey($raw)) {
            continue
        }
        $skillName = [System.IO.Path]::GetFileName([System.IO.Path]::GetDirectoryName($raw.Replace('/', [System.IO.Path]::DirectorySeparatorChar)))
        $canonicalResult = Test-DoctorCanonicalSkill $canonicalFiles[$raw] $raw $skillName
        if ($canonicalResult.Valid) {
            $canonicalSkillDescriptions[$raw] = $canonicalResult.Description
        }
    }

    if ($claudeEnabled) {
        $nestedRaw = '.claude/CLAUDE.md'
        $topRaw = 'CLAUDE.md'
        $nestedPath = Resolve-DoctorPath $Root $nestedRaw 'Claude adapter'
        $topPath = Resolve-DoctorPath $Root $topRaw 'Claude adapter'
        $adapterRaw = $null
        if ($null -ne $nestedPath -and (Test-Path -LiteralPath $nestedPath -PathType Leaf)) {
            $adapterRaw = $nestedRaw
        }
        elseif ($null -ne $topPath -and (Test-Path -LiteralPath $topPath -PathType Leaf)) {
            $adapterRaw = $topRaw
        }
        if ($null -eq $adapterRaw) {
            Add-DoctorError 'Claude adapter is enabled but no CLAUDE.md exists'
        }
        else {
            [void]$expectedManaged.Add($adapterRaw)
            $adapterPath = Require-DoctorFile $Root $adapterRaw 'Claude adapter'
            $adapterText = if ($null -ne $adapterPath) { Read-DoctorUtf8 $adapterPath $adapterRaw } else { $null }
            $expectedImport = if (Test-DoctorExactString $adapterRaw $nestedRaw) { '@../AGENTS.md' } else { '@AGENTS.md' }
            $hasImport = $false
            if ($null -ne $adapterText) {
                foreach ($line in @($adapterText -split "`r?`n")) {
                    if ($line.Trim() -ceq $expectedImport) {
                        $hasImport = $true
                        break
                    }
                }
            }
            if ($null -ne $adapterText -and -not $hasImport) {
                Add-DoctorError "Claude adapter must contain standalone import $expectedImport"
            }
        }

        foreach ($raw in $rules) {
            $filename = [System.IO.Path]::GetFileName($raw)
            $adapterRaw = ".claude/rules/$filename"
            [void]$expectedManaged.Add($adapterRaw)
            $adapterPath = Require-DoctorFile $Root $adapterRaw "Claude rule adapter for $raw"
            if ($null -ne $adapterPath) {
                $adapterText = Read-DoctorUtf8 $adapterPath $adapterRaw
            }
            else {
                $adapterText = $null
            }
            if ($null -ne $adapterText) {
                $marker = "<!-- ultracode-canonical: $raw -->"
                $frontmatter = Get-DoctorStrictFrontmatter $adapterText $adapterRaw
                if ($null -ne $frontmatter) {
                    $actualKeys = @($frontmatter.Keys.Keys)
                    if ($actualKeys.Count -ne 1 -or $actualKeys[0] -cne 'paths') {
                        Add-DoctorError "$adapterRaw frontmatter must contain exactly the paths key"
                    }
                    $pathsResult = Get-DoctorJsonYamlList $frontmatter.Front 'paths' $adapterRaw
                    if ($pathsResult.Valid) {
                        $paths = @($pathsResult.Values)
                        $uniquePaths = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
                        foreach ($pathValue in $paths) { [void]$uniquePaths.Add($pathValue) }
                        if ($uniquePaths.Count -ne $paths.Count) {
                            Add-DoctorError "$adapterRaw.paths contains duplicates"
                        }
                        $configuredPaths = if ($rulePaths.ContainsKey($raw)) { @($rulePaths[$raw]) } else { @() }
                        if (($paths -join "`n") -cne ($configuredPaths -join "`n")) {
                            Add-DoctorError "$adapterRaw.paths must exactly match artifacts.rule_paths['$raw']"
                        }
                        $expectedFrontmatter = 'paths:'
                        foreach ($pathValue in $paths) {
                            $expectedFrontmatter += "`n  - $(ConvertTo-DoctorJsonString $pathValue)"
                        }
                        if ($frontmatter.Front -cne $expectedFrontmatter) {
                            Add-DoctorError "$adapterRaw frontmatter differs from the deterministic rule adapter"
                        }
                    }
                    $tick = [char]96
                    $directive = "Read and follow the canonical rule at ${tick}${raw}${tick} completely before applying this adapter."
                    $expectedBody = $marker + "`n`n" + $directive
                    if ($frontmatter.Body -cne $expectedBody) {
                        Add-DoctorError "$adapterRaw body differs from the deterministic canonical rule adapter"
                    }
                }
            }
        }

        foreach ($raw in $skills) {
            $skillName = [System.IO.Path]::GetFileName([System.IO.Path]::GetDirectoryName($raw.Replace('/', [System.IO.Path]::DirectorySeparatorChar)))
            $adapterRaw = ".claude/skills/$skillName/SKILL.md"
            [void]$expectedManaged.Add($adapterRaw)
            $adapterPath = Require-DoctorFile $Root $adapterRaw "Claude skill adapter for $raw"
            if ($null -ne $adapterPath) {
                $adapterText = Read-DoctorUtf8 $adapterPath $adapterRaw
            }
            else {
                $adapterText = $null
            }
            if ($null -ne $adapterText) {
                $marker = "<!-- ultracode-canonical: $raw -->"
                $frontmatter = Get-DoctorStrictFrontmatter $adapterText $adapterRaw
                if ($null -ne $frontmatter) {
                    $actualKeys = @($frontmatter.Keys.Keys | Sort-Object)
                    if (($actualKeys -join "`n") -cne (@('description', 'name') -join "`n")) {
                        Add-DoctorError "$adapterRaw frontmatter must contain exactly name and description"
                    }
                    if (-not $frontmatter.Keys.ContainsKey('name') -or $frontmatter.Keys['name'] -cne $skillName) {
                        Add-DoctorError "$adapterRaw name must match canonical skill name $skillName"
                    }
                    $rawDescription = if ($frontmatter.Keys.ContainsKey('description')) { $frontmatter.Keys['description'] } else { '' }
                    $descriptionResult = Get-DoctorJsonYamlScalar $rawDescription "$adapterRaw.description"
                    if ($descriptionResult.Valid) {
                        if ($canonicalSkillDescriptions.ContainsKey($raw) -and $descriptionResult.Value -cne $canonicalSkillDescriptions[$raw]) {
                            Add-DoctorError "$adapterRaw.description must exactly match its canonical skill description"
                        }
                        $expectedFrontmatter = "name: $skillName`ndescription: $(ConvertTo-DoctorJsonString $descriptionResult.Value)"
                        if ($frontmatter.Front -cne $expectedFrontmatter) {
                            Add-DoctorError "$adapterRaw frontmatter differs from the deterministic skill adapter"
                        }
                    }
                    $tick = [char]96
                    $directive = "Read and follow the canonical skill at ${tick}${raw}${tick} completely before executing this skill."
                    $expectedBody = $marker + "`n`n" + $directive
                    if ($frontmatter.Body -cne $expectedBody) {
                        Add-DoctorError "$adapterRaw body differs from the deterministic canonical skill adapter"
                    }
                }
            }
        }
    }

    $commands = Require-DoctorObject $Config 'commands'
    foreach ($key in $script:commandKeys) {
        $entries = Get-ObjectProperty $commands $key
        if ($entries -isnot [System.Array]) {
            Add-DoctorError "commands.$key must be an array"
            continue
        }
        $seenEntries = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
        for ($index = 0; $index -lt $entries.Count; $index++) {
            $entry = $entries[$index]
            $marker = if (Test-DoctorObject $entry) { $entry | ConvertTo-Json -Compress -Depth 20 } else { [string]$entry }
            if (-not $seenEntries.Add($marker)) {
                Add-DoctorError "commands.$key contains a duplicate entry"
            }
            if (-not (Test-DoctorObject $entry)) {
                Add-DoctorError "commands.${key}[$index] must contain a command string"
                continue
            }
            $command = Get-ObjectProperty $entry 'command'
            $evidence = Get-ObjectProperty $entry 'evidence'
            if ($command -isnot [string] -or [string]::IsNullOrEmpty($command)) {
                Add-DoctorError "commands.${key}[$index] must contain a command string"
            }
            elseif (-not (Test-DoctorExactStringIn $evidence $script:evidenceStates)) {
                Add-DoctorError "commands.${key}[$index].evidence is invalid"
            }
            elseif (-not (Test-DoctorExactString $evidence 'VERIFIED')) {
                Add-DoctorWarning "commands.${key}[$index] remains $evidence"
            }
        }
    }

    $completion = Require-DoctorObject $Config 'completion'
    [void]@(Get-DoctorStringList (Get-ObjectProperty $completion 'required_checks') 'completion.required_checks')
    if ((Get-ObjectProperty $completion 'real_path') -isnot [string]) {
        Add-DoctorError 'completion.real_path must be a string'
    }
    if (-not (Test-DoctorExactStringIn (Get-ObjectProperty $completion 'review') @('independent-for-material-change', 'independent-for-critical-only', 'repository-policy'))) {
        Add-DoctorError 'completion.review is invalid'
    }

    $roles = Get-ObjectProperty $Config 'roles'
    if ($roles -isnot [System.Array]) {
        Add-DoctorError 'roles must be an array'
    }
    else {
        $roleIds = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
        for ($index = 0; $index -lt $roles.Count; $index++) {
            $role = $roles[$index]
            if (-not (Test-DoctorObject $role)) {
                Add-DoctorError "roles[$index] must be an object"
                continue
            }
            $roleId = Get-ObjectProperty $role 'id'
            if (-not (Test-DoctorRegex $roleId $script:kebabPattern)) {
                Add-DoctorError "roles[$index].id must be kebab-case"
                continue
            }
            if (-not $roleIds.Add($roleId)) {
                Add-DoctorError "duplicate role id: $roleId"
            }
            $rolePurpose = Get-ObjectProperty $role 'purpose'
            if ($rolePurpose -isnot [string]) {
                $rolePurpose = ''
            }
            if ([string]::IsNullOrWhiteSpace($rolePurpose)) {
                Add-DoctorError "roles[$index].purpose must be a non-empty string"
            }
            if (-not (Test-DoctorExactStringIn (Get-ObjectProperty $role 'mode') @('read-only', 'workspace-write'))) {
                Add-DoctorError "roles[$index].mode is invalid"
            }
            $roleSkills = @(Get-DoctorStringList (Get-ObjectProperty $role 'skills') "roles[$index].skills")

            $canonicalRaw = ".agents/reviewers/$roleId.md"
            [void]$expectedManaged.Add($canonicalRaw)
            $canonicalPath = Require-DoctorFile $Root $canonicalRaw "canonical reviewer $roleId"
            if ($null -eq $canonicalPath) {
                continue
            }
            $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $canonicalPath).Hash.ToLowerInvariant()
            $roleMode = Get-ObjectProperty $role 'mode'
            if ($roleMode -isnot [string]) {
                $roleMode = ''
            }
            if ($codexEnabled) {
                $codexRaw = ".codex/agents/$roleId.toml"
                [void]$expectedManaged.Add($codexRaw)
                $codexPath = Require-DoctorFile $Root $codexRaw "Codex role projection $roleId"
                if ($null -ne $codexPath) {
                    Test-DoctorCodexRoleProjection $codexPath $codexRaw $sourceHash $roleId $rolePurpose $roleMode $canonicalRaw
                }
            }
            if ($claudeEnabled) {
                $claudeRaw = ".claude/agents/$roleId.md"
                [void]$expectedManaged.Add($claudeRaw)
                $claudePath = Require-DoctorFile $Root $claudeRaw "Claude role projection $roleId"
                if ($null -ne $claudePath) {
                    Test-DoctorClaudeRoleProjection $claudePath $claudeRaw $sourceHash $roleId $rolePurpose $roleMode $canonicalRaw $roleSkills
                }
            }
        }
    }

    return [pscustomobject]@{
        ExpectedManaged = $expectedManaged
        StatusPath = if ($statusPathRaw -is [string]) { $statusPathRaw } else { $null }
        CanonicalArtifacts = @($canonicalArtifacts)
    }
}

function Test-DoctorManifest {
    param(
        $Manifest,
        [string]$Root,
        [AllowNull()][string]$StatusPath,
        [System.Collections.Generic.HashSet[string]]$ExpectedManaged
    )

    if (-not (Test-DoctorIntegerOne (Get-ObjectProperty $Manifest 'schema_version'))) {
        Add-DoctorError 'managed.schema_version must be 1'
    }
    if (-not (Test-DoctorExactStringIn (Get-ObjectProperty $Manifest 'generated_by') @('ultracode-init', 'ultracode-edit'))) {
        Add-DoctorError 'managed.generated_by must be ultracode-init or ultracode-edit'
    }
    $entries = Get-ObjectProperty $Manifest 'entries'
    if ($entries -isnot [System.Array]) {
        Add-DoctorError 'managed.entries must be an array'
        return
    }
    if ($entries.Count -lt 3) {
        Add-DoctorError 'managed.entries is incomplete; at least config, AGENTS.md, and canonical context are required'
    }

    $seen = New-Object 'System.Collections.Generic.Dictionary[string,object]' ([System.StringComparer]::Ordinal)
    for ($index = 0; $index -lt $entries.Count; $index++) {
        $entry = $entries[$index]
        $label = "managed.entries[$index]"
        if (-not (Test-DoctorObject $entry)) {
            Add-DoctorError "$label must be an object"
            continue
        }
        $rawPath = Get-ObjectProperty $entry 'path'
        if ($rawPath -isnot [string]) {
            Add-DoctorError "$label.path must be a string"
            continue
        }
        if (-not (Test-DoctorRegex $rawPath $script:managedPathPattern)) {
            Add-DoctorError "$label.path does not match the portable managed-path grammar: $rawPath"
        }
        if ($seen.ContainsKey($rawPath)) {
            Add-DoctorError "duplicate managed path: $rawPath"
            continue
        }
        $seen.Add($rawPath, $entry)
        if (
            (Test-DoctorExactString $rawPath '.ultracode/managed.json') -or
            ($null -ne $StatusPath -and (Test-DoctorExactString $rawPath $StatusPath))
        ) {
            Add-DoctorError "ephemeral or self-owned path cannot be managed: $rawPath"
        }
        $path = Resolve-DoctorPath $Root $rawPath "$label.path"
        if ($null -eq $path) {
            continue
        }
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            Add-DoctorError "managed file is missing: $rawPath"
            continue
        }
        $expectedHash = Get-ObjectProperty $entry 'sha256'
        if (-not (Test-DoctorRegex $expectedHash $script:sha256Pattern)) {
            Add-DoctorError "$label.sha256 must be a lowercase SHA-256"
            continue
        }
        $mode = Get-ObjectProperty $entry 'mode'
        $actualHash = $null
        if (Test-DoctorExactString $mode 'file') {
            if ((Test-ObjectProperty $entry 'start') -or (Test-ObjectProperty $entry 'end')) {
                Add-DoctorError "$label file mode must not define block markers"
            }
            if ((Test-DoctorExactString $rawPath '.claude/CLAUDE.md') -or (Test-DoctorExactString $rawPath 'CLAUDE.md')) {
                $expectedImport = if (Test-DoctorExactString $rawPath '.claude/CLAUDE.md') { '@../AGENTS.md' } else { '@AGENTS.md' }
                $adapterText = Read-DoctorUtf8 $path $rawPath
                if ($null -ne $adapterText -and (ConvertTo-DoctorLf $adapterText).Trim() -cne $expectedImport) {
                    Add-DoctorError "$rawPath file projection must contain exactly $expectedImport"
                }
            }
            $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        }
        elseif (Test-DoctorExactString $mode 'block') {
            $start = Get-ObjectProperty $entry 'start'
            $end = Get-ObjectProperty $entry 'end'
            if ($start -isnot [string] -or [string]::IsNullOrEmpty($start) -or $end -isnot [string] -or [string]::IsNullOrEmpty($end)) {
                Add-DoctorError "$label block mode requires start and end markers"
                continue
            }
            $text = Read-DoctorUtf8 $path "managed block file $rawPath"
            if ($null -eq $text) {
                continue
            }
            $capturedBlock = $null
            $actualHash = Get-DoctorBlockHash $text $start $end $rawPath ([ref]$capturedBlock)
            if ($null -ne $capturedBlock) {
                if ((Test-DoctorExactString $rawPath '.claude/CLAUDE.md') -or (Test-DoctorExactString $rawPath 'CLAUDE.md')) {
                    $expectedImport = if (Test-DoctorExactString $rawPath '.claude/CLAUDE.md') { '@../AGENTS.md' } else { '@AGENTS.md' }
                    $expectedStart = '<!-- ultracode:claude-root:start -->'
                    $expectedEnd = '<!-- ultracode:claude-root:end -->'
                    $expectedBlock = $expectedStart + "`n" + $expectedImport + "`n" + $expectedEnd
                    if ($start -cne $expectedStart -or $end -cne $expectedEnd -or $capturedBlock -cne $expectedBlock) {
                        Add-DoctorError "$rawPath block projection must be the exact ultracode:claude-root import block"
                    }
                }
            }
        }
        else {
            Add-DoctorError "$label.mode must be file or block"
            continue
        }
        if ($null -ne $actualHash -and $actualHash -cne $expectedHash) {
            Add-DoctorDrift "managed content changed: $rawPath"
        }
    }

    $missing = New-Object 'System.Collections.Generic.List[string]'
    foreach ($raw in $ExpectedManaged) {
        if (-not $seen.ContainsKey($raw)) {
            [void]$missing.Add($raw)
        }
    }
    if ($missing.Count -gt 0) {
        $sorted = @($missing | Sort-Object)
        Add-DoctorError "managed manifest omits configured artifacts: $(Format-DoctorPathList $sorted)"
    }
    $extras = New-Object 'System.Collections.Generic.List[string]'
    foreach ($raw in $seen.Keys) {
        if (-not $ExpectedManaged.Contains($raw)) {
            [void]$extras.Add($raw)
        }
    }
    if ($extras.Count -gt 0) {
        $sorted = @($extras | Sort-Object)
        Add-DoctorWarning "managed manifest contains disabled or unregistered artifacts: $(Format-DoctorPathList $sorted)"
    }

    if ($seen.ContainsKey('.ultracode/config.json') -and -not (Test-DoctorExactString (Get-ObjectProperty $seen['.ultracode/config.json'] 'mode') 'file')) {
        Add-DoctorError '.ultracode/config.json must use managed mode file'
    }
    if ($seen.ContainsKey('AGENTS.md') -and -not (Test-DoctorExactString (Get-ObjectProperty $seen['AGENTS.md'] 'mode') 'block')) {
        Add-DoctorError 'AGENTS.md must use a managed block'
    }
    elseif ($seen.ContainsKey('AGENTS.md') -and (
        (Get-ObjectProperty $seen['AGENTS.md'] 'start') -cne '<!-- ultracode:project:start -->' -or
        (Get-ObjectProperty $seen['AGENTS.md'] 'end') -cne '<!-- ultracode:project:end -->'
    )) {
        Add-DoctorError 'AGENTS.md must use the exact ultracode:project marker pair'
    }
}

$root = $null
$rootIsDirectory = $false
try {
    $rootItem = Get-Item -Force -LiteralPath $ProjectRoot
    if (-not $rootItem.PSIsContainer) {
        throw 'not a directory'
    }
    $root = $rootItem.FullName
    if (($rootItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        Add-DoctorError "project root traverses a symlink, junction, or reparse point: $root"
    }
    else {
        $rootIsDirectory = $true
    }
}
catch {
    try {
        $root = [System.IO.Path]::GetFullPath($ProjectRoot)
    }
    catch {
        $root = [string]$ProjectRoot
    }
    Add-DoctorError "project root is not a directory: $root"
}

if ($rootIsDirectory) {
    $configPath = Resolve-DoctorPath $root '.ultracode/config.json' '.ultracode/config.json'
    $manifestPath = Resolve-DoctorPath $root '.ultracode/managed.json' '.ultracode/managed.json'
    $config = if ($null -ne $configPath) { Read-DoctorJson $configPath } else { $null }
    $manifest = if ($null -ne $manifestPath) { Read-DoctorJson $manifestPath } else { $null }
    $configResult = $null
    if ($null -ne $config) {
        $configResult = Test-DoctorConfig $config $root
    }
    if ($null -ne $manifest) {
        $expectedManaged = if ($null -ne $configResult) {
            $configResult.ExpectedManaged
        }
        else {
            New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
        }
        $configuredStatusPath = if ($null -ne $configResult) { $configResult.StatusPath } else { $null }
        Test-DoctorManifest $manifest $root $configuredStatusPath $expectedManaged
    }
}

$status = if ($script:doctorErrors.Count -gt 0) { 'FAILED' } elseif ($script:doctorDrift.Count -gt 0) { 'DRIFT' } else { 'PASSED' }
$result = [ordered]@{
    status = $status
    project_root = $root
    errors = @($script:doctorErrors)
    drift = @($script:doctorDrift)
    warnings = @($script:doctorWarnings)
}

if ($Json) {
    $result | ConvertTo-Json -Depth 8
}
else {
    Write-Output "UltraCode project doctor: $status"
    foreach ($item in $script:doctorErrors) { Write-Output "ERROR: $item" }
    foreach ($item in $script:doctorDrift) { Write-Output "DRIFT: $item" }
    foreach ($item in $script:doctorWarnings) { Write-Output "WARNING: $item" }
}

if ($status -eq 'FAILED') { exit 1 }
if ($status -eq 'DRIFT') { exit 2 }
exit 0
