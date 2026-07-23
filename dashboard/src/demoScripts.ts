/** Production investigation prompts shown as quick-action chips. */
export const DEMO_SCRIPTS = [
  {
    id: "1",
    label: "剧本1 · KPI",
    question: "当前数据范围内，整体评论情感分布和负面率是多少？",
  },
  {
    id: "2",
    label: "剧本2 · 差评商品",
    question: "负面率最高的几个商品是什么？主要差在哪些方面或原因？",
  },
  {
    id: "3",
    label: "剧本3 · 方面",
    question: "目前差评主要集中在哪些方面（如尺码、材质、物流相关）？",
  },
  {
    id: "4",
    label: "剧本4 · 尺码方面",
    question: "size（尺码）方面的负面提及情况怎样？",
  },
] as const;
