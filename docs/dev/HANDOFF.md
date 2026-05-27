# Handoff — <date>

<!--
  这是 MindForge 低 context 交接文档。
  当 context < 15% 时由 /mf-autopilot 写入。
  新 session 启动时 /mf-autopilot 必须读取此文件（如果存在）。
  新 loop 成功启动后应删除或标记 resolved。
-->

## Repo Snapshot
- HEAD: <hash>
- Branch: main
- Working tree: clean / dirty
- vs origin/main: <left> <right>

## Active Workstream
- Workstream: <name>
- Status: <in-progress / blocked / done>

## Last Completed Loop
- Task type: <type>
- Outcome: <1 sentence>
- Commit: <hash>

## In-Progress Files
- <file1> (staged / unstaged / pending)
- <file2>

## Gates Last Run
- <command>: exit <N>

## Next /mf-autopilot Instruction
```
/mf-autopilot

继续 <workstream>。
上次在 <exact file> 完成了 <exact thing>。
下一步: <concrete next action>。
```

## Hard Stops / Warnings
- <any active hard-stop conditions>
- <context remaining estimate>
