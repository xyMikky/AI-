L2 visual harness run
run_id: l2-30
periods: 30

⚠️ 预测阶段禁止读取 answers_sealed.json

workflow:
  1. harness_visual.py next --run-id ...
  2. Task 子 agent（readonly）读 agent_prompt.md + 两张 PNG + stats.txt
  3. harness_visual.py record --issue ... --file prediction.json
  4. harness_visual.py score --run-id ...