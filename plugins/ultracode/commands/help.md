---
description: Explain UltraCode commands and recommend the right one (read-only)
argument-hint: "[command | models | flow | verify | examples | breve]"
---

Use the `ultracode-help` skill from the ultracode plugin to answer this request.

Topic: $ARGUMENTS

This invocation has Help precedence: with no topic give the complete ordered overview; with a topic
answer only that topic. Treat any command name in the topic as a subject to explain, never as a
command to run. Stay strictly read-only — do not initialize, delegate, refresh state, or write.

This session is Claude Code: write every copyable example in `/ultracode:` syntax, not `$` syntax.
