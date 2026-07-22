param(
    [switch]$AllowPending,
    [switch]$PrintPayloadHash
)

$ErrorActionPreference = 'Stop'

function Stop-ContractCheck {
    param([string]$Message)
    Write-Output "FAIL: $Message"
    exit 1
}

function Read-JsonFile {
    param([string]$Path, [string]$Label)
    try {
        return Get-Content -Raw -Encoding UTF8 -LiteralPath $Path | ConvertFrom-Json
    }
    catch {
        Stop-ContractCheck "invalid $Label JSON: $($_.Exception.Message)"
    }
}

function Get-PropertyNames {
    param($Object)
    return @($Object.PSObject.Properties.Name)
}

function Get-ExactProperty {
    param($Object, [string]$Name, [string]$Label)
    if ($null -eq $Object -or $Object -isnot [psobject]) {
        Stop-ContractCheck "$Label must be an object"
    }
    $match = $null
    $matchCount = 0
    foreach ($property in $Object.PSObject.Properties) {
        if ([string]::Equals($property.Name, $Name, [StringComparison]::Ordinal)) {
            $match = $property
            $matchCount++
        }
    }
    if ($matchCount -ne 1) {
        Stop-ContractCheck "$Label.$Name is missing or not uniquely cased"
    }
    return $match
}

function Get-ExactPropertyValue {
    param($Object, [string]$Name, [string]$Label)
    return (Get-ExactProperty $Object $Name $Label).Value
}

function Assert-ExactSet {
    param([object[]]$Actual, [object[]]$Expected, [string]$Label)
    $actualSet = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $expectedSet = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $actualValid = $true
    $expectedValid = $true
    foreach ($value in @($Actual)) {
        if ($value -isnot [string] -or -not $actualSet.Add([string]$value)) { $actualValid = $false }
    }
    foreach ($value in @($Expected)) {
        if ($value -isnot [string] -or -not $expectedSet.Add([string]$value)) { $expectedValid = $false }
    }
    if (-not $actualValid -or -not $expectedValid -or -not $actualSet.SetEquals($expectedSet)) {
        $actualValues = [string[]]@($actualSet)
        $expectedValues = [string[]]@($expectedSet)
        [Array]::Sort($actualValues, [StringComparer]::Ordinal)
        [Array]::Sort($expectedValues, [StringComparer]::Ordinal)
        $actualText = $actualValues -join ', '
        $expectedText = $expectedValues -join ', '
        Stop-ContractCheck "$Label differs; expected=[$expectedText], actual=[$actualText]"
    }
}

function Assert-ExactProperties {
    param($Object, [string[]]$Expected, [string]$Label)
    if ($null -eq $Object -or $Object -isnot [psobject]) {
        Stop-ContractCheck "$Label must be an object"
    }
    Assert-ExactSet (Get-PropertyNames $Object) $Expected "$Label keys"
}

function Require-NonEmptyString {
    param($Value, [string]$Label)
    if ($Value -isnot [string] -or [string]::IsNullOrWhiteSpace($Value)) {
        Stop-ContractCheck "$Label must be a non-empty string"
    }
    return [string]$Value
}

function Test-ContractExactString {
    param($Value, [string]$Expected)
    return $Value -is [string] -and [string]::Equals(
        $Value,
        $Expected,
        [StringComparison]::Ordinal
    )
}

function Test-ContractExactStringIn {
    param($Value, [string[]]$Allowed)
    if ($Value -isnot [string]) { return $false }
    foreach ($candidate in $Allowed) {
        if ([string]::Equals($Value, $candidate, [StringComparison]::Ordinal)) { return $true }
    }
    return $false
}

function Test-ContractInteger {
    param($Value)
    foreach ($type in @([byte],[sbyte],[int16],[uint16],[int32],[uint32],[int64],[uint64])) {
        if ($Value -is $type) { return $true }
    }
    return $false
}

function Test-ContractIntegerEqual {
    param($Value, [int64]$Expected)
    return (Test-ContractInteger $Value) -and ([int64]$Value -eq $Expected)
}

function Test-ContractExactBoolean {
    param($Value, [bool]$Expected)
    return $Value -is [bool] -and $Value -eq $Expected
}

function ConvertTo-OrdinalDictionary {
    param([System.Collections.IDictionary]$Source, [string]$Label)
    $map = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    foreach ($entry in $Source.GetEnumerator()) {
        $key = Require-NonEmptyString $entry.Key "$Label key"
        if ($map.ContainsKey($key)) { Stop-ContractCheck "internal error: duplicate $Label key: $key" }
        $map.Add($key, $entry.Value)
    }
    return $map
}

function ConvertTo-UniqueMap {
    param($Items, [string]$Key, [string]$Label)
    $array = @($Items)
    if ($array.Count -eq 0) { Stop-ContractCheck "$Label must be a non-empty array" }
    $map = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    for ($index = 0; $index -lt $array.Count; $index++) {
        $item = $array[$index]
        if ($null -eq $item -or $item -isnot [psobject]) {
            Stop-ContractCheck "$Label[$index] must be an object"
        }
        $property = Get-ExactProperty $item $Key "$Label[$index]"
        $identity = Require-NonEmptyString $property.Value "$Label[$index].$Key"
        if ($map.ContainsKey($identity)) { Stop-ContractCheck "$Label contains duplicate $Key`: $identity" }
        $map.Add($identity, $item)
    }
    return $map
}

function Get-PluginPayloadSha256 {
    param([string]$Root)
    $excluded = @(
        'skills/ultracode/references/evaluation-evidence.json',
        'skills/ultracode/references/evaluation-traces.json'
    )
    $rootFull = [IO.Path]::GetFullPath($Root).TrimEnd([char[]]@('\','/'))
    $files = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
    $rootItem = Get-Item -Force -LiteralPath $rootFull
    if (($rootItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        Stop-ContractCheck 'plugin payload root cannot be a symlink or reparse point'
    }
    $visit = $null
    $visit = {
        param([string]$Directory)
        foreach ($item in Get-ChildItem -Force -LiteralPath $Directory) {
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                Stop-ContractCheck "plugin payload contains a symlink or reparse entry: $($item.FullName)"
            }
            if ($item.PSIsContainer) {
                & $visit $item.FullName
                continue
            }
            $relative = $item.FullName.Substring($rootFull.Length).TrimStart([char[]]@('\','/')).Replace('\','/')
            if (-not (Test-ContractExactStringIn $relative $excluded)) { $files.Add($relative, $item.FullName) }
        }
    }
    try {
        & $visit $rootFull
    }
    catch {
        Stop-ContractCheck "cannot enumerate plugin payload: $($_.Exception.Message)"
    }
    $paths = [string[]]@($files.Keys)
    [Array]::Sort($paths, [StringComparer]::Ordinal)
    $hasher = [Security.Cryptography.IncrementalHash]::CreateHash(
        [Security.Cryptography.HashAlgorithmName]::SHA256
    )
    $utf8 = [Text.UTF8Encoding]::new($false)
    $nul = [byte[]]@(0)
    try {
        foreach ($relative in $paths) {
            $hasher.AppendData($utf8.GetBytes($relative))
            $hasher.AppendData($nul)
            $hasher.AppendData([IO.File]::ReadAllBytes($files[$relative]))
            $hasher.AppendData($nul)
        }
        $bytes = $hasher.GetHashAndReset()
    }
    catch {
        Stop-ContractCheck "cannot hash plugin payload: $($_.Exception.Message)"
    }
    finally {
        $hasher.Dispose()
    }
    return -join ($bytes | ForEach-Object { $_.ToString('x2') })
}

function Assert-ResultShape {
    param($Item, [string]$Kind, [string]$Label, [string[]]$ValidStatuses)
    if (Test-ContractExactString $Kind 'scenario') {
        Assert-ExactProperties $Item @('id','status','trace_id','evidence') $Label
    }
    elseif (Test-ContractExactStringIn $Kind @('fixture','validation')) {
        Assert-ExactProperties $Item @('check','status','command','exit_code','trace_id','evidence') $Label
        [void](Require-NonEmptyString (Get-ExactPropertyValue $Item 'command' $Label) "$Label.command")
    }
    elseif (Test-ContractExactString $Kind 'audit') {
        Assert-ExactProperties $Item @('check','severity','status','trace_id','evidence') $Label
        if (-not (Test-ContractExactStringIn (Get-ExactPropertyValue $Item 'severity' $Label) @('HIGH','MEDIUM','LOW'))) {
            Stop-ContractCheck "$Label.severity is invalid"
        }
    }
    else {
        Stop-ContractCheck "internal error: unknown result kind $Kind"
    }
    $status = Get-ExactPropertyValue $Item 'status' $Label
    if (-not (Test-ContractExactStringIn $status $ValidStatuses)) { Stop-ContractCheck "$Label.status is invalid" }
    $traceId = Require-NonEmptyString (Get-ExactPropertyValue $Item 'trace_id' $Label) "$Label.trace_id"
    if ($traceId -cnotmatch '^trace-[a-z0-9][a-z0-9-]*$') { Stop-ContractCheck "$Label.trace_id is invalid" }
    [void](Require-NonEmptyString (Get-ExactPropertyValue $Item 'evidence' $Label) "$Label.evidence")
}

function Assert-ExecutableResult {
    param($Item, [string]$Label)
    $status = Get-ExactPropertyValue $Item 'status' $Label
    $exitCode = Get-ExactPropertyValue $Item 'exit_code' $Label
    if (Test-ContractExactStringIn $status @('PENDING','NOT_AVAILABLE')) {
        if ($null -ne $exitCode) { Stop-ContractCheck "$Label must use null exit_code while $status" }
        return
    }
    if (-not (Test-ContractInteger $exitCode)) {
        Stop-ContractCheck "$Label must record an integer exit_code after execution"
    }
    $statusExits = ConvertTo-OrdinalDictionary @{ PASSED = 0; FAILED = 1; DRIFT = 2 } 'status exit'
    if (-not $statusExits.ContainsKey($status)) { Stop-ContractCheck "$Label status has no executable exit mapping" }
    $expectedExit = $statusExits[$status]
    if (-not (Test-ContractIntegerEqual $exitCode $expectedExit)) {
        Stop-ContractCheck "$Label status $status must use exit_code $expectedExit"
    }
}

function Bind-ResultTrace {
    param($Item, [string]$Category, [string]$SubjectProperty, $Records)
    $traceId = [string](Get-ExactPropertyValue $Item 'trace_id' 'result')
    if (-not $Records.ContainsKey($traceId)) { Stop-ContractCheck "result references missing trace: $traceId" }
    $record = $Records[$traceId]
    $recordCategory = Get-ExactPropertyValue $record 'category' "trace $traceId"
    $recordSubject = Get-ExactPropertyValue $record 'subject' "trace $traceId"
    $recordStatus = Get-ExactPropertyValue $record 'status' "trace $traceId"
    if (-not (Test-ContractExactString $recordCategory $Category)) { Stop-ContractCheck "trace $traceId category does not match $Category" }
    $subject = Get-ExactPropertyValue $Item $SubjectProperty 'result'
    $itemStatus = Get-ExactPropertyValue $Item 'status' 'result'
    if (-not (Test-ContractExactString $recordSubject $subject) -or -not (Test-ContractExactString $recordStatus $itemStatus)) {
        Stop-ContractCheck "trace $traceId subject or status does not match its result"
    }
    if (Test-ContractExactStringIn $Category @('fixture','validation')) {
        $recordExitCode = Get-ExactPropertyValue $record 'exit_code' "trace $traceId"
        $itemExitCode = Get-ExactPropertyValue $Item 'exit_code' 'result'
        $exitCodesMatch = if ($null -eq $recordExitCode -and $null -eq $itemExitCode) {
            $true
        }
        elseif ($null -ne $recordExitCode -and $null -ne $itemExitCode -and (Test-ContractInteger $itemExitCode)) {
            Test-ContractIntegerEqual $recordExitCode ([int64]$itemExitCode)
        }
        else {
            $false
        }
        $recordCommand = Get-ExactPropertyValue $record 'command' "trace $traceId"
        $itemCommand = Get-ExactPropertyValue $Item 'command' 'result'
        if (-not (Test-ContractExactString $recordCommand $itemCommand) -or -not $exitCodesMatch) {
            Stop-ContractCheck "trace $traceId command or exit_code does not match its result"
        }
    }
    return $traceId
}

function Get-ContractPowerShellExecutable {
    foreach ($candidate in @((Join-Path $PSHOME 'powershell.exe'),(Join-Path $PSHOME 'pwsh.exe'),(Join-Path $PSHOME 'pwsh'))) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    $command = Get-Command powershell.exe,pwsh -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $command) { Stop-ContractCheck 'cannot locate PowerShell for the live doctor corpus' }
    return $command.Source
}

function Quote-ContractProcessArgument {
    param([string]$Value)
    return '"' + $Value.Replace('"','\"') + '"'
}

function Invoke-LivePowerShellCorpus {
    param([string]$CoreRoot)
    $harness = Join-Path $CoreRoot 'scripts\run_doctor_corpus.ps1'
    $doctor = Join-Path $CoreRoot 'scripts\project_doctor.ps1'
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = Get-ContractPowerShellExecutable
    $start.Arguments = "-NoProfile -ExecutionPolicy Bypass -File $(Quote-ContractProcessArgument $harness)"
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.CreateNoWindow = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        [void]$process.Start()
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        $processExit = $process.ExitCode
    }
    catch {
        Stop-ContractCheck "cannot execute PowerShell live doctor corpus: $($_.Exception.Message)"
    }
    finally {
        $process.Dispose()
    }
    try { $report = $stdout | ConvertFrom-Json }
    catch {
        $detail = if ([string]::IsNullOrWhiteSpace($stderr)) { $stdout.Trim() } else { $stderr.Trim() }
        Stop-ContractCheck "invalid PowerShell live corpus JSON: $($_.Exception.Message); output=$detail"
    }
    Assert-ExactProperties $report @('schema_version','runtime','doctor_sha256','cases','summary') 'PowerShell live corpus report'
    $reportSchemaVersion = Get-ExactPropertyValue $report 'schema_version' 'PowerShell live corpus report'
    $reportRuntime = Get-ExactPropertyValue $report 'runtime' 'PowerShell live corpus report'
    if (-not (Test-ContractIntegerEqual $reportSchemaVersion 1) -or -not (Test-ContractExactString $reportRuntime 'powershell')) {
        Stop-ContractCheck 'PowerShell live corpus report identity is invalid'
    }
    $doctorHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $doctor).Hash.ToLowerInvariant()
    if (-not (Test-ContractExactString (Get-ExactPropertyValue $report 'doctor_sha256' 'PowerShell live corpus report') $doctorHash)) {
        Stop-ContractCheck 'PowerShell live corpus report does not bind the current doctor'
    }
    $expected = ConvertTo-OrdinalDictionary ([ordered]@{
        valid=@('PASSED',0); drift=@('DRIFT',2); 'empty-manifest'=@('FAILED',1)
        'omitted-config'=@('FAILED',1); 'broken-claude-root-import'=@('FAILED',1)
        'claude-root-extra-body'=@('FAILED',1); casing=@('FAILED',1)
        'config-key-casing'=@('FAILED',1); 'artifact-id-casing'=@('FAILED',1)
        'role-id-casing'=@('FAILED',1)
        'semantic-rule-adapter'=@('FAILED',1); 'semantic-skill-adapter'=@('FAILED',1)
        'semantic-skill-adapter-contrary'=@('FAILED',1); 'invalid-managed-block'=@('FAILED',1)
        'invalid-managed-block-key'=@('FAILED',1); 'invalid-managed-path-char'=@('FAILED',1)
        'rich-valid'=@('PASSED',0); 'role-valid'=@('PASSED',0)
        'duplicate-claude-role-key'=@('FAILED',1); 'extra-claude-role-key'=@('FAILED',1)
        reparse=@('FAILED',1); 'missing-config-route'=@('FAILED',1)
        'boolean-control-plan'=@('FAILED',1); 'boolean-authority'=@('FAILED',1)
        'boolean-decomposition'=@('FAILED',1); 'boolean-concurrency'=@('FAILED',1)
        'boolean-model-policy'=@('FAILED',1); 'boolean-command-evidence'=@('FAILED',1)
        'boolean-completion-review'=@('FAILED',1); 'boolean-generated-by'=@('FAILED',1)
        'boolean-manifest-mode'=@('FAILED',1); 'boolean-config-schema'=@('FAILED',1)
        'boolean-manifest-schema'=@('FAILED',1); 'boolean-synthesis'=@('FAILED',1)
        'canonical-skill-missing-frontmatter'=@('FAILED',1)
        'skill-description-mismatch'=@('FAILED',1)
    }) 'PowerShell live corpus expected cases'
    $cases = ConvertTo-UniqueMap (Get-ExactPropertyValue $report 'cases' 'PowerShell live corpus report') 'id' 'PowerShell live corpus cases'
    Assert-ExactSet @($cases.Keys) @($expected.Keys) 'PowerShell live corpus case set'
    $mismatches = [Collections.Generic.List[string]]::new()
    $unavailable = [Collections.Generic.List[string]]::new()
    foreach ($caseId in $cases.Keys) {
        $item = $cases[$caseId]
        Assert-ExactProperties $item @('id','expected_status','expected_exit','actual_status','actual_exit','outcome','diagnostics') "PowerShell live corpus case $caseId"
        $expectedResult = $expected[$caseId]
        $expectedStatus = Get-ExactPropertyValue $item 'expected_status' "PowerShell live corpus case $caseId"
        $expectedExit = Get-ExactPropertyValue $item 'expected_exit' "PowerShell live corpus case $caseId"
        $actualStatus = Get-ExactPropertyValue $item 'actual_status' "PowerShell live corpus case $caseId"
        $actualExit = Get-ExactPropertyValue $item 'actual_exit' "PowerShell live corpus case $caseId"
        $outcome = Get-ExactPropertyValue $item 'outcome' "PowerShell live corpus case $caseId"
        if (-not (Test-ContractExactString $expectedStatus $expectedResult[0]) -or -not (Test-ContractIntegerEqual $expectedExit ([int64]$expectedResult[1]))) {
            Stop-ContractCheck "PowerShell live corpus case $caseId changed its expected result"
        }
        foreach ($diagnostic in @(Get-ExactPropertyValue $item 'diagnostics' "PowerShell live corpus case $caseId")) {
            if ($diagnostic -isnot [string]) { Stop-ContractCheck "PowerShell live corpus case $caseId diagnostics must be strings" }
        }
        if (Test-ContractExactString $outcome 'NOT_AVAILABLE') {
            if (-not (Test-ContractExactString $actualStatus 'NOT_AVAILABLE') -or $null -ne $actualExit) {
                Stop-ContractCheck "PowerShell live corpus case $caseId has malformed NOT_AVAILABLE state"
            }
            [void]$unavailable.Add($caseId)
        }
        elseif (Test-ContractExactString $outcome 'MATCH') {
            if (-not (Test-ContractExactString $actualStatus $expectedResult[0]) -or -not (Test-ContractIntegerEqual $actualExit ([int64]$expectedResult[1]))) {
                Stop-ContractCheck "PowerShell live corpus case $caseId claims a false match"
            }
        }
        else { [void]$mismatches.Add($caseId) }
    }
    $summary = Get-ExactPropertyValue $report 'summary' 'PowerShell live corpus report'
    Assert-ExactProperties $summary @('total','matched','mismatched','not_available') 'PowerShell live corpus summary'
    $expectedMatched = $expected.Count - $mismatches.Count - $unavailable.Count
    if (
        -not (Test-ContractIntegerEqual (Get-ExactPropertyValue $summary 'total' 'PowerShell live corpus summary') $expected.Count) -or
        -not (Test-ContractIntegerEqual (Get-ExactPropertyValue $summary 'matched' 'PowerShell live corpus summary') $expectedMatched) -or
        -not (Test-ContractIntegerEqual (Get-ExactPropertyValue $summary 'mismatched' 'PowerShell live corpus summary') $mismatches.Count) -or
        -not (Test-ContractIntegerEqual (Get-ExactPropertyValue $summary 'not_available' 'PowerShell live corpus summary') $unavailable.Count)
    ) { Stop-ContractCheck 'PowerShell live corpus summary does not match its case records' }
    if ($unavailable.Count -ne 0) {
        Stop-ContractCheck "PowerShell live corpus cases are NOT_AVAILABLE: $(@($unavailable) -join ', ')"
    }
    if ($mismatches.Count -ne 0 -or $processExit -ne 0) {
        Stop-ContractCheck "PowerShell live corpus failed; process_exit=$processExit, mismatches=$(@($mismatches) -join ', ')"
    }
}

$coreRoot = Split-Path -Parent $PSScriptRoot
$skillsRoot = Split-Path -Parent $coreRoot
$pluginRoot = Split-Path -Parent $skillsRoot
$referenceRoot = Join-Path $coreRoot 'references'
$manifestPath = Join-Path $pluginRoot '.codex-plugin\plugin.json'
$skillNames = @('ultracode','ultracode-init','ultracode-edit','ultracode-status')
$validStatuses = @('PASSED','FAILED','DRIFT','PENDING','NOT_AVAILABLE')

if ($PrintPayloadHash) {
    Write-Output (Get-PluginPayloadSha256 $pluginRoot)
    exit 0
}

foreach ($path in @($skillsRoot, (Join-Path $coreRoot 'SKILL.md'), $referenceRoot, $manifestPath)) {
    if (-not (Test-Path -LiteralPath $path)) { Stop-ContractCheck "missing required path: $path" }
}

$skillHashes = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
foreach ($skillName in $skillNames) {
    $skillRoot = Join-Path $skillsRoot $skillName
    $skillPath = Join-Path $skillRoot 'SKILL.md'
    $metadataPath = Join-Path $skillRoot 'agents\openai.yaml'
    if (-not (Test-Path -LiteralPath $skillPath -PathType Leaf) -or -not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) {
        Stop-ContractCheck "missing skill or metadata for $skillName"
    }
    $skillText = Get-Content -Raw -Encoding UTF8 -LiteralPath $skillPath
    if ($skillText.Contains('TODO')) { Stop-ContractCheck "$skillName/SKILL.md contains TODO text" }
    if ((Get-Content -Encoding UTF8 -LiteralPath $skillPath).Count -ge 500) {
        Stop-ContractCheck "$skillName/SKILL.md must remain under 500 lines"
    }
    if ($skillText -cnotmatch "(?m)^name:\s*$([regex]::Escape($skillName))\s*$") {
        Stop-ContractCheck "$skillName/SKILL.md frontmatter name is invalid"
    }
    $metadataText = Get-Content -Raw -Encoding UTF8 -LiteralPath $metadataPath
    if (-not $metadataText.Contains('$' + $skillName)) {
        Stop-ContractCheck "$skillName/agents/openai.yaml must mention `$$skillName"
    }
    $skillHashes.Add($skillName, (Get-FileHash -Algorithm SHA256 -LiteralPath $skillPath).Hash.ToLowerInvariant())
}

$coreText = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $coreRoot 'SKILL.md')
$requiredCoreClauses = @(
    'Do not run build, test, formatter, generator, package, or editor commands',
    'Label self-review as non-independent',
    'The problem structure determines the logical job count',
    'one adversarial verifier to each material finding',
    'exactly one synthesis owner',
    'queue the remainder in visible waves',
    'hard_safety_cap` is a circuit breaker, not a target',
    'a read-only task remains read-only',
    'Limit the automatic fix-review loop to two iterations',
    'Treat staging, committing, pushing, deploying, publishing'
)
foreach ($clause in $requiredCoreClauses) {
    if (-not $coreText.Contains($clause)) { Stop-ContractCheck "missing core contract clause: $clause" }
}

$references = @(
    'routing-and-delegation.md',
    'validation-and-review.md',
    'project-adapter.md',
    'swarm-protocol.md',
    'control-and-status.md',
    'behavioral-contract.md',
    'eval-prompts.md'
)
foreach ($reference in $references) {
    if (-not (Test-Path -LiteralPath (Join-Path $referenceRoot $reference) -PathType Leaf)) {
        Stop-ContractCheck "missing reference: $reference"
    }
    if (-not $coreText.Contains("references/$reference")) { Stop-ContractCheck "core SKILL.md does not route to $reference" }
}
$resources = @(
    'references\project-config.schema.json',
    'references\managed-manifest.schema.json',
    'references\evaluation-evidence.schema.json',
    'references\evaluation-traces.json',
    'references\evaluation-evidence.json',
    'scripts\project_doctor.py',
    'scripts\project_doctor.ps1',
    'scripts\run_contract_casing_corpus.py',
    'scripts\run_doctor_corpus.py',
    'scripts\run_doctor_corpus.ps1'
)
foreach ($relative in $resources) {
    if (-not (Test-Path -LiteralPath (Join-Path $coreRoot $relative) -PathType Leaf)) {
        Stop-ContractCheck "missing core resource: $relative"
    }
}
Invoke-LivePowerShellCorpus $coreRoot
foreach ($schemaName in @('project-config.schema.json','managed-manifest.schema.json','evaluation-evidence.schema.json')) {
    [void](Read-JsonFile (Join-Path $referenceRoot $schemaName) $schemaName)
}

$initText = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $skillsRoot 'ultracode-init\SKILL.md')
foreach ($required in @('project-config.schema.json','Do not ask how many swarm agents','.ultracode/managed.json','.git/info/exclude')) {
    if (-not $initText.Contains($required)) { Stop-ContractCheck "ultracode-init is missing: $required" }
}
$editText = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $skillsRoot 'ultracode-edit\SKILL.md')
foreach ($required in @('project_doctor','managed.json','Never ask for an agent count','Do not delete automatically')) {
    if (-not $editText.Contains($required)) { Stop-ContractCheck "ultracode-edit is missing: $required" }
}
$statusText = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $skillsRoot 'ultracode-status\SKILL.md')
foreach ($required in @('Stay read-only','logical jobs versus currently live agent instances','Never invent percentages')) {
    if (-not $statusText.Contains($required)) { Stop-ContractCheck "ultracode-status is missing: $required" }
}

$contractText = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $referenceRoot 'behavioral-contract.md')
foreach ($index in 1..34) {
    $scenario = 'UC-{0:D2}' -f $index
    if (-not $contractText.Contains($scenario)) { Stop-ContractCheck "missing behavioral scenario: $scenario" }
}
$promptText = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $referenceRoot 'eval-prompts.md')
$requiredPrompts = @(
    'UC-01','UC-03','UC-04','UC-06','UC-08','UC-10','UC-14','UC-18','UC-19',
    'UC-20','UC-23','UC-24','UC-25','UC-26','UC-29','UC-30','UC-31','UC-32','UC-33','UC-34'
)
foreach ($scenario in $requiredPrompts) {
    if (-not $promptText.Contains($scenario)) { Stop-ContractCheck "missing forward-test prompt: $scenario" }
}

$manifest = Read-JsonFile $manifestPath 'plugin manifest'
$manifestName = Get-ExactPropertyValue $manifest 'name' 'plugin manifest'
$manifestSkills = Get-ExactPropertyValue $manifest 'skills' 'plugin manifest'
if (-not (Test-ContractExactString $manifestName 'ultracode') -or -not (Test-ContractExactString $manifestSkills './skills/')) {
    Stop-ContractCheck 'plugin manifest identity or skill path is invalid'
}
if (Test-ContractExactStringIn 'hooks' (Get-PropertyNames $manifest)) { Stop-ContractCheck 'unsupported hooks field must not be present' }
$manifestInterface = Get-ExactPropertyValue $manifest 'interface' 'plugin manifest'
$defaultPrompts = @(Get-ExactPropertyValue $manifestInterface 'defaultPrompt' 'plugin manifest.interface')
if (-not ($defaultPrompts | Where-Object { $_ -is [string] -and $_.Contains('$ultracode-init') })) {
    Stop-ContractCheck 'plugin default prompts must expose $ultracode-init'
}
if (-not ($defaultPrompts | Where-Object { $_ -is [string] -and $_.Contains('$ultracode-status') })) {
    Stop-ContractCheck 'plugin default prompts must expose $ultracode-status'
}

$schema = Read-JsonFile (Join-Path $referenceRoot 'evaluation-evidence.schema.json') 'evaluation evidence schema'
$schemaType = Get-ExactPropertyValue $schema 'type' 'evaluation evidence schema'
$schemaAdditionalProperties = Get-ExactPropertyValue $schema 'additionalProperties' 'evaluation evidence schema'
$schemaRequired = @(Get-ExactPropertyValue $schema 'required' 'evaluation evidence schema')
$schemaProperties = Get-ExactPropertyValue $schema 'properties' 'evaluation evidence schema'
if (-not (Test-ContractExactString $schemaType 'object') -or -not (Test-ContractExactBoolean $schemaAdditionalProperties $false)) {
    Stop-ContractCheck 'evaluation evidence schema must close the root object'
}
$evidenceKeys = @(
    'schema_version','attestation_scope','plugin_version_prefix','evaluated_on','skill_sha256','payload_sha256',
    'trace_artifact','trace_sha256','scenario_results','fixture_results','validation_results','audit_results'
)
Assert-ExactSet $schemaRequired $evidenceKeys 'evaluation evidence schema required fields'
Assert-ExactSet (Get-PropertyNames $schemaProperties) $evidenceKeys 'evaluation evidence schema property fields'
$schemaVersionDefinition = Get-ExactPropertyValue $schemaProperties 'schema_version' 'evaluation evidence schema.properties'
$attestationDefinition = Get-ExactPropertyValue $schemaProperties 'attestation_scope' 'evaluation evidence schema.properties'
$traceArtifactDefinition = Get-ExactPropertyValue $schemaProperties 'trace_artifact' 'evaluation evidence schema.properties'
if (-not (Test-ContractIntegerEqual (Get-ExactPropertyValue $schemaVersionDefinition 'const' 'evaluation evidence schema.properties.schema_version') 2)) {
    Stop-ContractCheck 'evaluation evidence schema version must be const 2'
}
if (-not (Test-ContractExactString (Get-ExactPropertyValue $attestationDefinition 'const' 'evaluation evidence schema.properties.attestation_scope') 'local-consistency-only')) {
    Stop-ContractCheck 'evaluation evidence schema must pin local-consistency-only attestation scope'
}
if (-not (Test-ContractExactString (Get-ExactPropertyValue $traceArtifactDefinition 'const' 'evaluation evidence schema.properties.trace_artifact') 'evaluation-traces.json')) {
    Stop-ContractCheck 'evaluation evidence schema must pin the trace artifact name'
}
$expectedSchemaCounts = ConvertTo-OrdinalDictionary ([ordered]@{
    scenario_results = 12
    fixture_results = 10
    validation_results = 8
    audit_results = 1
}) 'evaluation schema result count'
foreach ($field in $expectedSchemaCounts.Keys) {
    $definition = Get-ExactPropertyValue $schemaProperties $field 'evaluation evidence schema.properties'
    $count = $expectedSchemaCounts[$field]
    $minItems = Get-ExactPropertyValue $definition 'minItems' "evaluation evidence schema.properties.$field"
    $maxItems = Get-ExactPropertyValue $definition 'maxItems' "evaluation evidence schema.properties.$field"
    $uniqueItems = Get-ExactPropertyValue $definition 'uniqueItems' "evaluation evidence schema.properties.$field"
    if (-not (Test-ContractIntegerEqual $minItems $count) -or -not (Test-ContractIntegerEqual $maxItems $count) -or -not (Test-ContractExactBoolean $uniqueItems $true)) {
        Stop-ContractCheck "evaluation evidence schema must pin $field to $count unique results"
    }
}
$skillHashDefinition = Get-ExactPropertyValue $schemaProperties 'skill_sha256' 'evaluation evidence schema.properties'
if (-not (Test-ContractExactBoolean (Get-ExactPropertyValue $skillHashDefinition 'additionalProperties' 'evaluation evidence schema.properties.skill_sha256') $false)) {
    Stop-ContractCheck 'evaluation evidence schema must close skill_sha256'
}
Assert-ExactSet @(Get-ExactPropertyValue $skillHashDefinition 'required' 'evaluation evidence schema.properties.skill_sha256') $skillNames 'evaluation schema skill hashes'
$schemaDefinitions = Get-ExactPropertyValue $schema '$defs' 'evaluation evidence schema'
$statusDefinition = Get-ExactPropertyValue $schemaDefinitions 'status' 'evaluation evidence schema.$defs'
Assert-ExactSet @(Get-ExactPropertyValue $statusDefinition 'enum' 'evaluation evidence schema.$defs.status') $validStatuses 'evaluation schema statuses'

$evidencePath = Join-Path $referenceRoot 'evaluation-evidence.json'
$evidence = Read-JsonFile $evidencePath 'evaluation evidence'
Assert-ExactProperties $evidence $evidenceKeys 'evaluation evidence'
$evidenceSchemaVersion = Get-ExactPropertyValue $evidence 'schema_version' 'evaluation evidence'
$evidenceAttestationScope = Get-ExactPropertyValue $evidence 'attestation_scope' 'evaluation evidence'
$evidenceVersionPrefix = Get-ExactPropertyValue $evidence 'plugin_version_prefix' 'evaluation evidence'
$evidenceEvaluatedOn = Get-ExactPropertyValue $evidence 'evaluated_on' 'evaluation evidence'
$evidenceSkillHashes = Get-ExactPropertyValue $evidence 'skill_sha256' 'evaluation evidence'
$evidencePayloadHash = Get-ExactPropertyValue $evidence 'payload_sha256' 'evaluation evidence'
$evidenceTraceArtifact = Get-ExactPropertyValue $evidence 'trace_artifact' 'evaluation evidence'
$evidenceTraceHash = Get-ExactPropertyValue $evidence 'trace_sha256' 'evaluation evidence'
if (-not (Test-ContractIntegerEqual $evidenceSchemaVersion 2)) { Stop-ContractCheck 'evaluation evidence schema_version must be 2' }
if (-not (Test-ContractExactString $evidenceAttestationScope 'local-consistency-only')) {
    Stop-ContractCheck 'evaluation evidence must declare local-consistency-only attestation scope'
}
$manifestVersion = Require-NonEmptyString (Get-ExactPropertyValue $manifest 'version' 'plugin manifest') 'plugin manifest.version'
$versionPrefix = $manifestVersion -replace '\+.*$', ''
if (-not (Test-ContractExactString $evidenceVersionPrefix $versionPrefix)) {
    Stop-ContractCheck 'evaluation evidence version prefix does not match the plugin manifest'
}
$evaluatedOn = Require-NonEmptyString $evidenceEvaluatedOn 'evaluated_on'
$parsedDate = [datetime]::MinValue
if (-not [datetime]::TryParseExact(
    $evaluatedOn,
    'yyyy-MM-dd',
    [Globalization.CultureInfo]::InvariantCulture,
    [Globalization.DateTimeStyles]::None,
    [ref]$parsedDate
)) { Stop-ContractCheck 'evaluated_on must be an ISO date' }
Assert-ExactSet (Get-PropertyNames $evidenceSkillHashes) $skillNames 'evaluation evidence skill hashes'
foreach ($skillName in $skillNames) {
    $recordedHash = [string](Get-ExactPropertyValue $evidenceSkillHashes $skillName 'evaluation evidence.skill_sha256')
    if ($recordedHash -cnotmatch '^[0-9a-f]{64}$') { Stop-ContractCheck "evaluation evidence hash is invalid for $skillName" }
    if (-not (Test-ContractExactString $recordedHash $skillHashes[$skillName])) { Stop-ContractCheck "evaluation evidence hash mismatch for $skillName" }
}
$payloadHash = [string]$evidencePayloadHash
if ($payloadHash -cnotmatch '^[0-9a-f]{64}$') { Stop-ContractCheck 'evaluation evidence payload_sha256 is invalid' }
$actualPayloadHash = Get-PluginPayloadSha256 $pluginRoot
if (-not (Test-ContractExactString $payloadHash $actualPayloadHash)) {
    Stop-ContractCheck 'evaluation evidence payload_sha256 does not match the current plugin tree'
}

if (-not (Test-ContractExactString $evidenceTraceArtifact 'evaluation-traces.json')) {
    Stop-ContractCheck 'evaluation evidence must use evaluation-traces.json'
}
$tracePath = Join-Path $referenceRoot 'evaluation-traces.json'
$traceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $tracePath).Hash.ToLowerInvariant()
if (-not (Test-ContractExactString $evidenceTraceHash $traceHash)) {
    Stop-ContractCheck 'evaluation trace hash does not match evaluation-traces.json'
}
$traces = Read-JsonFile $tracePath 'evaluation traces'
Assert-ExactProperties $traces @('schema_version','attestation_scope','plugin_version_prefix','generated_on','records') 'evaluation traces'
$tracesSchemaVersion = Get-ExactPropertyValue $traces 'schema_version' 'evaluation traces'
$tracesVersionPrefix = Get-ExactPropertyValue $traces 'plugin_version_prefix' 'evaluation traces'
$tracesAttestationScope = Get-ExactPropertyValue $traces 'attestation_scope' 'evaluation traces'
$tracesGeneratedOn = Get-ExactPropertyValue $traces 'generated_on' 'evaluation traces'
if (-not (Test-ContractIntegerEqual $tracesSchemaVersion 1)) { Stop-ContractCheck 'evaluation traces schema_version must be 1' }
if (-not (Test-ContractExactString $tracesVersionPrefix $versionPrefix)) { Stop-ContractCheck 'evaluation traces plugin version does not match evidence' }
if (-not (Test-ContractExactString $tracesAttestationScope 'local-consistency-only')) {
    Stop-ContractCheck 'evaluation traces must declare local-consistency-only attestation scope'
}
if (-not (Test-ContractExactString $tracesGeneratedOn $evaluatedOn)) { Stop-ContractCheck 'evaluation traces date does not match evidence' }
$records = ConvertTo-UniqueMap (Get-ExactPropertyValue $traces 'records' 'evaluation traces') 'trace_id' 'trace records'
$traceProperties = @('trace_id','category','subject','status','source_type','command','exit_code','facts')
foreach ($traceId in $records.Keys) {
    $record = $records[$traceId]
    Assert-ExactProperties $record $traceProperties "trace record $traceId"
    if ($traceId -cnotmatch '^trace-[a-z0-9][a-z0-9-]*$') { Stop-ContractCheck "trace record ID is invalid: $traceId" }
    $recordCategory = Get-ExactPropertyValue $record 'category' "trace record $traceId"
    $recordSubject = Get-ExactPropertyValue $record 'subject' "trace record $traceId"
    $recordStatus = Get-ExactPropertyValue $record 'status' "trace record $traceId"
    $recordCommand = Get-ExactPropertyValue $record 'command' "trace record $traceId"
    $recordExitCode = Get-ExactPropertyValue $record 'exit_code' "trace record $traceId"
    if (-not (Test-ContractExactStringIn $recordCategory @('scenario','fixture','validation','audit'))) { Stop-ContractCheck "trace record $traceId has invalid category" }
    [void](Require-NonEmptyString $recordSubject "trace record $traceId.subject")
    if (-not (Test-ContractExactStringIn $recordStatus $validStatuses)) { Stop-ContractCheck "trace record $traceId has invalid status" }
    $sourceType = Require-NonEmptyString (Get-ExactPropertyValue $record 'source_type' "trace record $traceId") "trace record $traceId.source_type"
    if (-not (Test-ContractExactStringIn $sourceType @('fresh-agent-result','command-result','independent-audit-result','planned','planned-command'))) {
        Stop-ContractCheck "trace record $traceId has invalid source_type"
    }
    if ($null -ne $recordCommand -and ($recordCommand -isnot [string] -or [string]::IsNullOrWhiteSpace($recordCommand))) {
        Stop-ContractCheck "trace record $traceId.command must be null or non-empty"
    }
    if ($null -ne $recordExitCode -and -not (Test-ContractInteger $recordExitCode)) {
        Stop-ContractCheck "trace record $traceId.exit_code must be null or integer"
    }
    $facts = @(Get-ExactPropertyValue $record 'facts' "trace record $traceId")
    if ($facts.Count -eq 0 -or @($facts | Where-Object { $_ -isnot [string] -or [string]::IsNullOrWhiteSpace($_) }).Count -ne 0) {
        Stop-ContractCheck "trace record $traceId.facts must contain non-empty strings"
    }
    if (Test-ContractExactString $recordStatus 'PENDING') {
        $expectedSource = if (Test-ContractExactStringIn $recordCategory @('fixture','validation')) { 'planned-command' } else { 'planned' }
        if (-not (Test-ContractExactString $sourceType $expectedSource) -or $null -ne $recordExitCode) {
            Stop-ContractCheck "pending trace $traceId must be explicitly planned and unexecuted"
        }
    }
    else {
        $expectedSourcesByCategory = ConvertTo-OrdinalDictionary ([ordered]@{
            scenario = @('fresh-agent-result','command-result')
            fixture = @('command-result')
            validation = @('command-result')
            audit = @('independent-audit-result')
        }) 'trace category source'
        if (-not $expectedSourcesByCategory.ContainsKey($recordCategory)) {
            Stop-ContractCheck "trace record $traceId has no source policy for its category"
        }
        $expectedSources = $expectedSourcesByCategory[$recordCategory]
        if (-not (Test-ContractExactStringIn $sourceType $expectedSources)) {
            Stop-ContractCheck "executed trace $traceId has an invalid source_type for $recordCategory"
        }
    }
}

$pending = [Collections.Generic.List[string]]::new()
$referenced = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)

$requiredEvidenceScenarios = @('UC-01','UC-03','UC-04','UC-19','UC-23','UC-24','UC-25','UC-29','UC-30','UC-31','UC-32','UC-34')
$scenarios = ConvertTo-UniqueMap (Get-ExactPropertyValue $evidence 'scenario_results' 'evaluation evidence') 'id' 'scenario_results'
Assert-ExactSet @($scenarios.Keys) $requiredEvidenceScenarios 'scenario_results'
foreach ($scenarioId in $scenarios.Keys) {
    $item = $scenarios[$scenarioId]
    Assert-ResultShape $item 'scenario' "scenario $scenarioId" $validStatuses
    [void]$referenced.Add((Bind-ResultTrace $item 'scenario' 'id' $records))
    $itemStatus = Get-ExactPropertyValue $item 'status' "scenario $scenarioId"
    if (Test-ContractExactString $itemStatus 'PENDING') { [void]$pending.Add("scenario:$scenarioId") }
    elseif (-not (Test-ContractExactString $itemStatus 'PASSED')) { Stop-ContractCheck "release scenario $scenarioId must pass" }
}

$expectedFixtures = ConvertTo-OrdinalDictionary ([ordered]@{
    'valid project fixture Python' = @('PASSED',0)
    'valid project fixture PowerShell' = @('PASSED',0)
    'managed drift fixture Python' = @('DRIFT',2)
    'managed drift fixture PowerShell' = @('DRIFT',2)
    'incomplete managed manifest fixture Python' = @('FAILED',1)
    'incomplete managed manifest fixture PowerShell' = @('FAILED',1)
    'reparse boundary fixture Python' = @('FAILED',1)
    'reparse boundary fixture PowerShell' = @('FAILED',1)
    'semantic adapter mismatch fixture Python' = @('FAILED',1)
    'semantic adapter mismatch fixture PowerShell' = @('FAILED',1)
}) 'expected fixture result'
$expectedFixtureCommands = ConvertTo-OrdinalDictionary ([ordered]@{
    'valid project fixture Python' = '${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.py ${VALID_FIXTURE}'
    'valid project fixture PowerShell' = 'powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.ps1 -ProjectRoot ${VALID_FIXTURE}'
    'managed drift fixture Python' = '${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.py ${DRIFT_FIXTURE}'
    'managed drift fixture PowerShell' = 'powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.ps1 -ProjectRoot ${DRIFT_FIXTURE}'
    'incomplete managed manifest fixture Python' = '${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.py ${INCOMPLETE_MANIFEST_FIXTURE}'
    'incomplete managed manifest fixture PowerShell' = 'powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.ps1 -ProjectRoot ${INCOMPLETE_MANIFEST_FIXTURE}'
    'reparse boundary fixture Python' = '${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.py ${REPARSE_FIXTURE}'
    'reparse boundary fixture PowerShell' = 'powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.ps1 -ProjectRoot ${REPARSE_FIXTURE}'
    'semantic adapter mismatch fixture Python' = '${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.py ${SEMANTIC_ADAPTER_FIXTURE}'
    'semantic adapter mismatch fixture PowerShell' = 'powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/project_doctor.ps1 -ProjectRoot ${SEMANTIC_ADAPTER_FIXTURE}'
}) 'expected fixture command'
$fixtures = ConvertTo-UniqueMap (Get-ExactPropertyValue $evidence 'fixture_results' 'evaluation evidence') 'check' 'fixture_results'
Assert-ExactSet @($fixtures.Keys) @($expectedFixtures.Keys) 'fixture_results'
foreach ($check in $fixtures.Keys) {
    $item = $fixtures[$check]
    Assert-ResultShape $item 'fixture' "fixture $check" $validStatuses
    Assert-ExecutableResult $item "fixture $check"
    [void]$referenced.Add((Bind-ResultTrace $item 'fixture' 'check' $records))
    $itemCommand = Get-ExactPropertyValue $item 'command' "fixture $check"
    $itemStatus = Get-ExactPropertyValue $item 'status' "fixture $check"
    $itemExitCode = Get-ExactPropertyValue $item 'exit_code' "fixture $check"
    if (-not (Test-ContractExactString $itemCommand $expectedFixtureCommands[$check])) {
        Stop-ContractCheck "fixture $check command does not match the required command"
    }
    if (Test-ContractExactString $itemStatus 'PENDING') { [void]$pending.Add("fixture:$check") }
    else {
        $expected = $expectedFixtures[$check]
        if (-not (Test-ContractExactString $itemStatus $expected[0]) -or -not (Test-ContractIntegerEqual $itemExitCode $expected[1])) {
            Stop-ContractCheck "fixture $check must record $($expected[0]) with exit code $($expected[1])"
        }
    }
}

$expectedValidationCommands = ConvertTo-OrdinalDictionary ([ordered]@{
    'quick_validate ultracode' = 'uv run --offline --with pyyaml -- python ${SKILL_CREATOR}/scripts/quick_validate.py ${PLUGIN_ROOT}/skills/ultracode'
    'quick_validate ultracode-init' = 'uv run --offline --with pyyaml -- python ${SKILL_CREATOR}/scripts/quick_validate.py ${PLUGIN_ROOT}/skills/ultracode-init'
    'quick_validate ultracode-edit' = 'uv run --offline --with pyyaml -- python ${SKILL_CREATOR}/scripts/quick_validate.py ${PLUGIN_ROOT}/skills/ultracode-edit'
    'quick_validate ultracode-status' = 'uv run --offline --with pyyaml -- python ${SKILL_CREATOR}/scripts/quick_validate.py ${PLUGIN_ROOT}/skills/ultracode-status'
    'validate_plugin' = 'uv run --offline --with pyyaml -- python ${PLUGIN_CREATOR}/scripts/validate_plugin.py ${PLUGIN_ROOT}'
    'contract checker Python bootstrap' = '${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/check_contract.py --allow-pending'
    'contract checker PowerShell bootstrap' = 'powershell -File ${PLUGIN_ROOT}/skills/ultracode/scripts/check_contract.ps1 -AllowPending'
    'contract casing corpus' = '${PYTHON} ${PLUGIN_ROOT}/skills/ultracode/scripts/run_contract_casing_corpus.py'
}) 'expected validation command'
$requiredValidations = @($expectedValidationCommands.Keys)
$validations = ConvertTo-UniqueMap (Get-ExactPropertyValue $evidence 'validation_results' 'evaluation evidence') 'check' 'validation_results'
Assert-ExactSet @($validations.Keys) $requiredValidations 'validation_results'
foreach ($check in $validations.Keys) {
    $item = $validations[$check]
    Assert-ResultShape $item 'validation' "validation $check" $validStatuses
    Assert-ExecutableResult $item "validation $check"
    [void]$referenced.Add((Bind-ResultTrace $item 'validation' 'check' $records))
    $itemCommand = Get-ExactPropertyValue $item 'command' "validation $check"
    $itemStatus = Get-ExactPropertyValue $item 'status' "validation $check"
    $itemExitCode = Get-ExactPropertyValue $item 'exit_code' "validation $check"
    if (-not (Test-ContractExactString $itemCommand $expectedValidationCommands[$check])) {
        Stop-ContractCheck "validation $check command does not match the required command"
    }
    if (Test-ContractExactString $itemStatus 'PENDING') { [void]$pending.Add("validation:$check") }
    elseif (-not (Test-ContractExactString $itemStatus 'PASSED') -or -not (Test-ContractIntegerEqual $itemExitCode 0)) {
        Stop-ContractCheck "release validation $check must pass with exit code 0"
    }
}

$audits = ConvertTo-UniqueMap (Get-ExactPropertyValue $evidence 'audit_results' 'evaluation evidence') 'check' 'audit_results'
Assert-ExactSet @($audits.Keys) @('final independent high-severity audit') 'audit_results'
foreach ($check in $audits.Keys) {
    $item = $audits[$check]
    Assert-ResultShape $item 'audit' "audit $check" $validStatuses
    [void]$referenced.Add((Bind-ResultTrace $item 'audit' 'check' $records))
    $itemSeverity = Get-ExactPropertyValue $item 'severity' "audit $check"
    $itemStatus = Get-ExactPropertyValue $item 'status' "audit $check"
    if (-not (Test-ContractExactString $itemSeverity 'HIGH')) { Stop-ContractCheck 'final independent audit must cover high-severity findings' }
    if (Test-ContractExactString $itemStatus 'PENDING') { [void]$pending.Add("audit:$check") }
    elseif (-not (Test-ContractExactString $itemStatus 'PASSED')) { Stop-ContractCheck 'final independent high-severity audit must pass' }
}

Assert-ExactSet @($referenced) @($records.Keys) 'referenced evaluation trace IDs'

if ($pending.Count -ne 0) {
    $summary = (@($pending) | Sort-Object) -join ', '
    if (-not $AllowPending) {
        Write-Output "PENDING: release evidence is incomplete: $summary"
        exit 2
    }
    Write-Output "UltraCode contract structure passed with pending release evidence: $summary"
    exit 0
}

Write-Output 'UltraCode contract and release evidence checks passed'
