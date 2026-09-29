# 解说稿：每段是一次"换台"——一座城市的电台，用当地语言播报，配中文字幕。
# 画面编排在 render.py 里按段落 id 和关键词锚点对齐。

STATIONS = {
    # key: (电台城市标签, 语言标签, 刻度盘位置 0..1)
    "berlin":     ("BERLIN",      "DEUTSCH",  0.16),
    "nanking":    ("南京 NANKING", "中文",     0.30),
    "london":     ("LONDON",      "ENGLISH",  0.42),
    "warszawa":   ("WARSZAWA",    "POLSKI",   0.24),
    "paris":      ("PARIS",       "FRANÇAIS", 0.36),
    "moskva":     ("МОСКВА",      "РУССКИЙ",  0.55),
    "washington": ("WASHINGTON",  "ENGLISH",  0.72),
    "tokyo":      ("東京 TOKYO",   "日本語",    0.86),
}

VOICES = {
    "de": "de-DE-ConradNeural",
    "zh": "zh-CN-YunyangNeural",
    "gb": "en-GB-RyanNeural",
    "pl": "pl-PL-MarekNeural",
    "fr": "fr-FR-HenriNeural",
    "ru": "ru-RU-DmitryNeural",
    "us": "en-US-GuyNeural",
    "ja": "ja-JP-KeitaNeural",
}

# 每段：id, 电台, 语言, 原文(TTS), 中文字幕, 年, 月
# 原文和中文用 "|" 切成数量相同的字幕块，播报时逐块显示
# archival: 可选的真实原声（文件缺失时改为屏幕引语卡，不用合成声音冒充真人）
SEGMENTS = [
    dict(id="rhineland", st="berlin", lang="de", y=1936, m=3,
         text="Deutsche Truppen marschieren in das entmilitarisierte Rheinland ein.|"
              "Paris und London protestieren – und tun nichts.",
         zh="1936年3月，德军开进非军事区莱茵兰。|巴黎和伦敦提出抗议——然后什么也没做。"),
    dict(id="marcopolo", st="nanking", lang="zh", y=1937, m=7,
         text="卢沟桥的枪声响起，|全面抗战爆发。|12月，南京沦陷，日军屠城。",
         zh="卢沟桥的枪声响起，|全面抗战爆发。|12月，南京沦陷，日军屠城。"),
    dict(id="munich", st="london", lang="gb", y=1938, m=3,
         text="March 1938: Germany annexes Austria.|In September, at Munich, "
              "Britain and France hand Hitler the Sudetenland.",
         zh="1938年3月，德国吞并奥地利。|9月，慕尼黑——英法把苏台德拱手让给希特勒。",
         archival=dict(file="chamberlain_peace.wav", who="张伯伦", en="I believe it is peace for our time.",
                       zh="我相信，这是我们时代的和平。")),
    dict(id="poland", st="warszawa", lang="pl", y=1939, m=9,
         text="Uwaga, uwaga!|Wojska niemieckie przekroczyły granicę Polski.",
         zh="注意，注意！|德军越过波兰边境。"),
    dict(id="declare", st="london", lang="gb", y=1939, m=9,
         text="Britain and France declare war on Germany.",
         zh="9月3日，英法对德宣战。"),
    dict(id="france", st="paris", lang="fr", y=1940, m=5,
         text="Mai 1940. Les blindés allemands percent à travers les Ardennes.|"
              "Le 14 juin, ils défilent dans Paris.",
         zh="1940年5月，德军装甲部队突破阿登森林。|6月14日，他们开进了巴黎。"),
    dict(id="blitz", st="london", lang="gb", y=1940, m=9,
         text="Night after night, the bombers come.",
         zh="一夜又一夜，轰炸机飞临伦敦。"),
    dict(id="barbarossa", st="moskva", lang="ru", y=1941, m=6,
         text="Внимание, говорит Москва!|Без объявления войны германские войска напали на Советский Союз.",
         zh="注意，这里是莫斯科！|德军不宣而战，进攻苏联。"),
    dict(id="pearl", st="washington", lang="us", y=1941, m=12,
         text="Sunday morning, December seventh.|Japanese planes strike Pearl Harbor.",
         zh="12月7日，星期天早晨。|日本飞机突袭珍珠港。",
         archival=dict(file="fdr_infamy.wav", who="罗斯福",
                       en="Yesterday, December 7th, 1941 — a date which will live in infamy —",
                       zh="昨天，1941年12月7日——一个永远蒙受耻辱的日子。")),
    dict(id="southward", st="tokyo", lang="ja", y=1942, m=2,
         text="大本営発表。|帝国陸海軍は、香港、マニラ、シンガポールを、相次いで攻略せり。",
         zh="大本营发表：|帝国陆海军相继攻占香港、马尼拉、新加坡。"),
    dict(id="midway", st="washington", lang="us", y=1942, m=6,
         text="Midway.|Four Japanese carriers, sunk in a single day.",
         zh="中途岛。|日本四艘航母，一天之内全部沉没。"),
    dict(id="stalingrad", st="moskva", lang="ru", y=1943, m=2,
         text="Сталинград. Двести дней боёв.|Второго февраля шестая германская армия капитулировала.",
         zh="斯大林格勒。两百天的血战。|2月2日，德军第六集团军投降。"),
    dict(id="dday", st="london", lang="gb", y=1944, m=6,
         text="D-Day.|The Allies storm the beaches of Normandy.",
         zh="D日。|盟军冲上诺曼底海滩。"),
    dict(id="berlin", st="moskva", lang="ru", y=1945, m=5,
         text="Берлин взят!|Германия капитулировала.|Победа!",
         zh="柏林已被攻克！|德国投降。|胜利！"),
    dict(id="pacific", st="washington", lang="us", y=1945, m=6,
         text="But in the Pacific, Japan fights on.|Iwo Jima. Okinawa.",
         zh="但在太平洋，日本仍在死战。|硫磺岛。冲绳。"),
    # 结尾：广岛之后电台重新响起
    dict(id="truman", st="washington", lang="us", y=1945, m=8,
         text="Sixteen hours ago, an American airplane dropped one bomb on Hiroshima.|It is an atomic bomb.",
         zh="十六小时前，一架美国飞机向广岛投下了一枚炸弹。|这是一枚原子弹。",
         who="白宫声明",
         archival=dict(file="truman_hiroshima.wav", who="杜鲁门",
                       en="Sixteen hours ago an American airplane dropped one bomb on Hiroshima.",
                       zh="十六小时前，一架美国飞机向广岛投下了一枚炸弹。", replaces_tts=True)),
]

# 屏幕上的纯文字卡（无配音）
CARDS = {
    "china_alone": "此时，中国已独自抗战四年多",
    "hiroshima": ("1945.08.06", "08:15", "广岛 · 広島"),
    "nagasaki": ("1945.08.09", "11:02", "长崎 · 長崎"),
    "surrender": "六天后，日本宣布无条件投降。",
    "toll": "第二次世界大战，约七千万至八千五百万人死去。",
    "title": ("从莱茵兰到长崎", "1936 — 1945"),
}

RATE = "+20%"
