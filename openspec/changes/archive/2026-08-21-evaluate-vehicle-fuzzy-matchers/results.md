# Vehicle fuzzy matcher evaluation

环境：`conda run -n agent`，Python 3.11，RapidFuzz 3.14.5。

基线运行命令：

```bash
conda run -n agent python -m inorder_llm.vehicle_matching.report
```

样本集现在固定为 500 条，全部逐条写在 `src/inorder_llm/vehicle_matching/dataset.py` 中；运行时不再从 catalog 展开、自动生成或补齐。样本包含 211 条高置信度正向样本和 289 条明确应拒绝或需澄清的表达。运行结果：RapidFuzz、n-gram 和 ensemble 均为 precision=1.000、false-positive-rate=0.000、coverage=0.406、abstain-rate=0.594。短词、范围/近似/历史指代、混合实体和数字冲突均未自动接受；ensemble 仅接受两个 matcher 给出一致且通过保守规则的候选。

coverage 现在更接近“高置信度样本的自动处理比例”，不应单独作为好坏指标：拒绝样本本来就不应归一。当前三种策略在人工样本集上结果一致，但仍不能据此直接接入生产归一化。下一步应继续加入真实用户表达，重点覆盖错别字、口语缩写、上下文中的多车型词和规格组合。
