"""演示数据：用需求照妖镜照它自己。

搜索结果的标题和链接是真实存在的页面（2026 年 11 月检索），
摘要是作者用自己的话写的转述，不是原文。
"示例评论"是虚构的，只用来演示归类和判定流程。
"""

DEMO_IDEA = (
    "做一个帮人验证产品点子的 AI 工具：用户说出想做的产品，工具联网搜索，"
    "分析这个点子合不合理、有没有需求，然后教他做最基础的宣传。"
)

DEMO_ANSWERS = [
    "刚开始做副业、想卖小工具或虚拟产品的大学生和新手独立开发者。我自己就是其中之一。",
    "大多数人直接问 ChatGPT、DeepSeek 或豆包；更多人干脆不验证，做完发出去，没人看。",
    "我自己就卡在不知道需求在哪，前面做过几个项目都没人用。我在小红书和公众号写 AI 工具内容，能直接接触到同类人。",
]

DEMO_RESPONSES: dict[str, dict] = {
    "clarify": {
        "questions": [
            {
                "question": "第一批用户具体是谁？是想做副业的大学生、刚做出第一个工具的独立开发者，还是准备辞职创业的人？",
                "why": "这三群人在哪里出现、愿意付多少钱、需要多快的答案，完全不一样。",
            },
            {
                "question": "这些人现在想验证一个点子时，实际是怎么做的？",
                "why": "免费的通用 AI 很可能就是你最大的对手，得先知道你要替代的是什么。",
            },
            {
                "question": "为什么是你来做？你自己用这套方法验证过点子吗？",
                "why": "自己没跑通的方法，很难让别人相信。",
            },
        ]
    },
    "criteria": {
        "assumptions": [
            {
                "kind": "需求",
                "statement": "新手在动手写代码之前，愿意花几天时间验证点子。",
                "how_to_falsify": "访谈 5 个人，多数说「想到就做，从来不验证，也不打算」。",
            },
            {
                "kind": "需求",
                "statement": "直接问通用 AI 得到的答案，不能让他们放心做决定。",
                "how_to_falsify": "多数人说「问 DeepSeek 就够了」，并且说不出不满意的地方。",
            },
            {
                "kind": "渠道",
                "statement": "能在小红书、即刻这类地方低成本找到这群人。",
                "how_to_falsify": "两条帖子发出 7 天，主动私信少于 3 人。",
            },
            {
                "kind": "付费",
                "statement": "有人愿意为一次有人跟进的验证付 9.9 元。",
                "how_to_falsify": "10 天内没有一个人付定金。",
            },
        ],
        "criteria": [
            {
                "id": "c_demo1",
                "metric": "私信要内测资格的人数",
                "level": 3,
                "threshold": 5,
                "days": 7,
                "note": "只算主动私信或填表，评论区说想要不算",
            },
            {
                "id": "c_demo2",
                "metric": "付 9.9 元定金的人数",
                "level": 4,
                "threshold": 2,
                "days": 10,
                "note": "真实到账才算，可以承诺不满意全额退",
            },
        ],
        "keywords": ["AI 点子验证", "创业想法验证工具", "startup idea validator"],
    },
    "queries": {
        "queries": [
            {"query": "AI startup idea validator", "kind": "支持"},
            {"query": "独立开发者 验证需求 方法", "kind": "支持"},
            {"query": "AI idea validation limitations", "kind": "反对"},
            {"query": "ChatGPT validate startup idea", "kind": "反对"},
            {"query": "创业点子验证 免费 prompt", "kind": "反对"},
            {"query": "idea validator tool shut down", "kind": "反对"},
        ]
    },
    "evidence": {
        "evidence": [
            {"ref": 0, "claim": "一个 AI 工具目录就收录了约 50 款「产品验证」类工具，多数是免费增值，同类产品已经很多。", "stance": "反对", "level": 2},
            {"ref": 1, "claim": "已经有产品专门把目标用户定为学生创业者，和本产品想找的第一批用户重合。", "stance": "反对", "level": 1},
            {"ref": 2, "claim": "有竞品直接给出「做还是重新想」的结论。用户可能就想要一个明确答案，而本产品刻意不给。", "stance": "反对", "level": 1},
            {"ref": 9, "claim": "已经有人把验证流程整理成十几条免费 prompt，直接交给通用 AI 就能跑，替代成本几乎为零。", "stance": "反对", "level": 2},
            {"ref": 10, "claim": "有专门的教程教人直接用 ChatGPT 验证创业点子，说明不少人已经在这么做。", "stance": "反对", "level": 2},
            {"ref": 7, "claim": "有人在卖付费的上市前验证指南，说明「怎么验证」这件事有人愿意花钱学。", "stance": "支持", "level": 1},
            {"ref": 5, "claim": "「先卖再做」被反复推荐，用预售验证需求的方法本身有共识，本产品把它做成了流程。", "stance": "支持", "level": 0},
            {"ref": 8, "claim": "一篇文章指出 AI 能整理调研、设计访谈，但没有真实用户的行为证据，它证明不了需求。", "stance": "支持", "level": 0},
            {"ref": 11, "claim": "自动生成的验证报告给好几个点子都打了同样的高分，现有工具的乐观偏差是真实存在的。", "stance": "支持", "level": 0},
            {"ref": 4, "claim": "Product Hunt 上还有更多同类「点子测试」产品在发布。", "stance": "中性", "level": 1},
        ]
    },
    "experiment": {
        "days": [
            {"day": 1, "action": "发小红书帖子，私信入口放在正文最后一句。当天回复每一条私信。", "criterion_id": "c_demo1"},
            {"day": 2, "action": "约 2 个私信的人做 15 分钟语音访谈，只问他们过去验证点子的真实经历。", "criterion_id": None},
            {"day": 3, "action": "发即刻帖子，开放 9.9 元定金名额，写清楚交付什么、不满意怎么退。", "criterion_id": "c_demo2"},
            {"day": 4, "action": "在 1~2 个副业或独立开发社群发预约表单。", "criterion_id": "c_demo1"},
            {"day": 5, "action": "用本工具给已付定金的人跑完整流程，记录卡在哪一步。", "criterion_id": "c_demo2"},
            {"day": 6, "action": "把访谈原话粘贴进第 6 步归类，看言论和行动的比例。", "criterion_id": None},
            {"day": 7, "action": "对照锁定的标准数数字，不改标准，直接看判定。", "criterion_id": "c_demo1"},
        ],
        "posts": [
            {
                "channel": "小红书",
                "title": "做了 3 个工具都没人用，这次我先验证再写代码",
                "body": (
                    "之前做的几个小工具，发出去都没人用。回头看，问题都一样：做之前没确认过有没有人要。\n\n"
                    "问 AI 也没用，它很容易顺着你夸。所以我在做一个反过来的工具：\n"
                    "1. 先让你写下「出现什么结果我就放弃」\n"
                    "2. 再专门去找推翻你点子的资料\n"
                    "3. 最后给你一套 7 天就能跑完的验证帖\n\n"
                    "它不会告诉你点子好不好，只会告诉你现在有没有证据。"
                ),
                "cta": "想试的私信我你的点子，前 10 个人我亲自帮你跑一遍。",
                "criterion_id": "c_demo1",
            },
            {
                "channel": "即刻",
                "title": "",
                "body": (
                    "做产品前最该花的不是开发时间，是验证时间。\n"
                    "我把自己验证点子的流程做成了一个工具：先定好放弃条件，再找反对意见，再发帖测试一周。\n"
                    "现在想找几个人一起跑真实案例。"
                ),
                "cta": "付 9.9 元定金，我用这套流程陪你验证一个点子，7 天内没交付全额退。",
                "criterion_id": "c_demo2",
            },
            {
                "channel": "副业或独立开发社群",
                "title": "",
                "body": (
                    "有没有人和我一样，做完东西才发现没人要？\n"
                    "我在做一个帮人提前验证点子的小工具，不打分、不画饼，只帮你拿到真实用户的反应。"
                ),
                "cta": "填这个表预约内测（只要一个联系方式和你的点子）。",
                "criterion_id": "c_demo1",
            },
        ],
        "interview_questions": [
            "你上一个想做的东西是什么？从想到它到动手，中间隔了多久？",
            "那次你有没有做什么来确认有人要？具体做了什么？",
            "最后结果怎么样？现在回头看，哪一步最可惜？",
            "你上一次为「学怎么做产品、怎么起号」这类事情花钱，是买了什么？花了多少？",
            "你现在手上有没有一个还没动手的点子？如果有，你打算怎么判断要不要做？",
        ],
    },
    "observations": {
        "items": [
            {"text": "蹲一个！好想要", "label": "言论"},
            {"text": "已私信，我想做一个考研资料分享小程序，想先验证一下", "label": "承诺"},
            {"text": "直接问 DeepSeek 不就行了", "label": "否定"},
            {"text": "已付 9.9，帮我看看宠物食品测评号这个方向", "label": "付费"},
            {"text": "求内测，已填表", "label": "承诺"},
            {"text": "感觉没必要，想做就做呗", "label": "否定"},
            {"text": "这个思路挺好，先收藏了", "label": "言论"},
        ]
    },
}

DEMO_RAW_COMMENTS = """蹲一个！好想要
已私信，我想做一个考研资料分享小程序，想先验证一下
直接问 DeepSeek 不就行了
已付 9.9，帮我看看宠物食品测评号这个方向
求内测，已填表
感觉没必要，想做就做呗
这个思路挺好，先收藏了"""


def _r(title: str, url: str, snippet: str) -> dict:
    return {"title": title, "url": url, "snippet": snippet}


_RESULTS = [
    _r("Product Validation AI tools（topai.tools）", "https://topai.tools/s/product-validation",
       "AI 工具目录，产品验证分类下收录约 50 款工具，包括 IdeaProof、ValidatorAI 等，多为免费增值。"),
    _r("StartupValidator AI", "https://www.turbostarter.dev/ideas/ai/startupvalidator-ai",
       "面向学生创业者的验证平台构想：市场调研、竞品分析、痛点洞察，并给出 0~100 的验证分。"),
    _r("Ideation.biz", "https://index.dodopayments.com/https-ideation-biz",
       "输入点子生成验证报告：创业评分、需求分析、风险评估，以及做还是重新想的建议。"),
    _r("StartupDeckAI", "https://peerpush.com/p/startupdeckai",
       "把点子验证、市场规模估算、竞品对比、SWOT 和商业模式评估放进同一个平台。"),
    _r("Founderli Idea Tester", "https://www.producthunt.com/products/founderli-idea-tester",
       "Product Hunt 上发布的点子测试工具。"),
    _r("The Best Way to Validate Your Idea Is to Sell It Before You Build It", "https://blog.mean.ceo/?p=2806",
       "主张在开发前先卖：用预售和定金判断需求，而不是靠调研。"),
    _r("How solo developers can validate SaaS ideas on a budget", "https://fungies.io/how-solo-developers-can-validate-saas-ideas-on-a-budget.md",
       "面向独立开发者的低预算验证方法汇总。"),
    _r("Go-to-Market Validation Guide（Gumroad）", "https://jonathanmillspatrick.gumroad.com/l/gtm-validation-guide",
       "在 Gumroad 上售卖的上市前验证指南。"),
    _r("Can AI Help You Validate a Product Idea Before Building?（Verdent）", "https://www.verdent.ai/guides/answers/ai-validate-product-idea-before-building",
       "AI 能帮忙整理调研、设计访谈和原型，但没有真实目标用户的证据，证明不了需求；做不做应看客户行为。"),
    _r("Best AI prompts to validate an idea before you build（Rocket）", "https://www.rocket.new/blog/best-ai-prompts-to-validate-an-idea-before-you-build",
       "整理了 15 条 prompt，用通用 AI 测试需求、竞争和付费意愿。"),
    _r("How to Use ChatGPT to Validate a Startup Idea（Preuve）", "https://preuve.ai/blog/how-to-use-chatgpt-to-validate-a-startup-idea",
       "教程：直接用 ChatGPT 做创业点子验证。"),
    _r("AI-Powered Startup Idea Validator（AnotherWrapper 示例报告）", "https://anotherwrapper.com/tools/startup-idea-validator/ai-powered-startup-idea-validator-unlocking-success-before-you-launch",
       "自动生成的验证报告示例，给「AI 点子验证工具」这个点子打出 8/10 的市场潜力。"),
]

# 搜索词 → 结果。按顺序去重后，编号（ref）与上面 _RESULTS 的下标一致。
DEMO_SEARCH = {
    "AI startup idea validator": [_RESULTS[i] for i in (0, 1, 2, 3, 4)],
    "独立开发者 验证需求 方法": [_RESULTS[i] for i in (5, 6, 7)],
    "AI idea validation limitations": [_RESULTS[i] for i in (8,)],
    "ChatGPT validate startup idea": [_RESULTS[i] for i in (9, 10)],
    "创业点子验证 免费 prompt": [_RESULTS[i] for i in (9, 11)],
    "idea validator tool shut down": [],
}
