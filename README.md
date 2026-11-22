# জীববিজ্ঞান (`biobangla`)

> **বিজ্ঞানের নতুন আবিষ্কার, বাংলায় সহজ ব্যাখ্যা।**  
> একটি শিক্ষামূলক, অবাণিজ্যিক বাংলা বিজ্ঞান সাংবাদিকতা প্ল্যাটফর্ম — জীববিজ্ঞান ও চিকিৎসা জীববিজ্ঞানের সাম্প্রতিক গবেষণাপত্রের তথ্যনিষ্ঠ বাংলা বিশ্লেষণ।

---

## ১. প্রকল্পের সারসংক্ষেপ (Overview)

**জীববিজ্ঞান (`biobangla`)** আন্তর্জাতিক বৈজ্ঞানিক জার্নাল এবং উন্মুক্ত প্রিপ্রিন্ট সার্ভারে প্রকাশিত জীববিজ্ঞান ও বায়োমেডিক্যাল গবেষণার মূল প্রশ্ন, প্রেক্ষাপট, গবেষণা পদ্ধতি, প্রধান ফলাফল, বৈজ্ঞানিক গুরুত্ব এবং সীমাবদ্ধতা প্রমিত ও সহজ বাংলায় উপস্থাপন করে।

### প্রধান বৈশিষ্ট্যসমূহ
- **সম্পাদকীয় বিজ্ঞান সাময়িকী নকশা:** পরিচ্ছন্ন সাদা পটভূমি, গভীর নেভি (`#0B1F3A`) ও টিল (`#0F766E`) অ্যাকসেন্ট, `Noto Sans Bengali` টাইপোগ্রাফি এবং প্রতিটি বিভাগের জন্য মৌলিক `SVG/CSS` বৈজ্ঞানিক রেখাচিত্র (কোনো কপিরাইটযুক্ত প্রকাশকের ছবি অনুমতি ছাড়া ব্যবহৃত হয় না)।
- **দশটি বিশেষায়িত বিভাগ:** অণুজীববিজ্ঞান, জীবপ্রযুক্তি, জিনতত্ত্ব ও জিনোমিক্স, চিকিৎসা জীববিজ্ঞান, রোগপ্রতিরোধবিদ্যা, পরিবেশ ও জীববৈচিত্র্য, সামুদ্রিক জীববিজ্ঞান, উদ্ভিদবিজ্ঞান, প্রাণিবিজ্ঞান এবং বিবর্তন জীববিজ্ঞান।
- **কঠোর বৈজ্ঞানিক সততা (Build-time & Pipeline Invariants):**
  - মৌলিক গবেষণা (`original-research`), পর্যালোচনামূলক প্রবন্ধ (`review`), প্রিপ্রিন্ট (`preprint`) এবং সম্পাদকীয় বিশ্লেষণ (`editorial`) সুস্পষ্টভাবে পৃথক।
  - **প্রিপ্রিন্ট সুরক্ষা:** Zod কনটেন্ট স্কিমা এবং Python QC গেট উভয় স্তরেই নিশ্চিত করা হয়েছে যে প্রিপ্রিন্ট কখনোই `peer_reviewed: true` হিসেবে চিহ্নিত বা প্রকাশিত হতে পারবে না।
  - **গবেষণা মডেল পৃথকীকরণ:** *In-vitro* (কোষীয় পরীক্ষা), প্রাণী মডেল (*Animal study*) এবং মানব ক্লিনিক্যাল ট্রায়ালের পার্থক্য স্পষ্টভাবে প্রদর্শিত হয়।
- **স্ট্যাটিক পূর্ণাঙ্গ অনুসন্ধান (Pagefind):** বাংলা এবং ইংরেজি বৈজ্ঞানিক পরিভাষা (যেমন `CRISPR`, `mRNA`, `মাইক্রোবায়োম`, `DOI`) উভয় ভাষায় দ্রুত ক্লায়েন্ট-সাইড সার্চ।
- **এসইও ও ফিড:** স্বয়ংক্রিয় `sitemap-index.xml`, `robots.txt`, `rss.xml` (RSS 2.0), `atom.xml` (Atom 1.0), ক্যানোনিকাল ইউআরএল, Open Graph কার্ড এবং `NewsArticle` / `ScholarlyArticle` JSON-LD স্ট্রাকচার্ড ডেটা।
- **পৃথক Python 3.12 গবেষণা অটোমেশন ইঞ্জিন:** Europe PMC, PubMed (NCBI E-utilities), Crossref, bioRxiv, PLOS এবং কনফিগারযোগ্য ওপেন-সায়েন্স RSS/Atom ফিডের মডিউলার কালেক্টর, ডিডুপ্লিকেশন, লাইসেন্স যাচাই, প্রোভাইডার-নিরপেক্ষ AI রাইটার এবং স্বাধীন `PASS` / `REVIEW` / `FAIL` মান নিয়ন্ত্রণ গেট।

---

## ২. রিপোজিটরি কাঠামো (Repository Structure)

```text
biobangla/
├── config/                     # YAML কনফিগারেশন (উৎস, ১০টি বিভাগ, পরিভাষা অভিধান ও সম্পাদনা নিয়ম)
│   ├── categories.yaml
│   ├── editorial_rules.yaml
│   ├── glossary.yaml
│   └── sources.yaml
├── content/                    # প্রকাশিত বাংলা Markdown নিবন্ধ ও বিজ্ঞান সহায়িকা
│   ├── articles/               # গবেষণা প্রতিবেদন (YAML frontmatter + Markdown)
│   └── explainers/             # শিক্ষামূলক বিজ্ঞান সহায়িকা (Explainers)
├── public/                     # স্ট্যাটিক অ্যাসেট (.nojekyll, favicon.svg, og-default.svg, CNAME.example)
├── scripts/                    # ফ্রন্টএন্ড থেকে যৌক্তিকভাবে পৃথক Python 3.12 অটোমেশন ইঞ্জিন
│   ├── collectors/             # Europe PMC, PubMed, Crossref, bioRxiv, PLOS, RSS কালেক্টর
│   ├── processors/             # ডিডুপ্লিকেশন, শ্রেণিবিন্যাস ও লাইসেন্স পরীক্ষক
│   ├── ai/                     # প্রোভাইডার-নিরপেক্ষ AI ইন্টারফেস, লেখক ও স্বাধীন QC ভ্যালিডেটর
│   ├── publishing/             # Markdown জেনারেটর, REVIEW কিউ ও পাবলিকেশন অডিট লগার
│   ├── run_collect.py          # সংগ্রহ পাইপলাইন CLI
│   └── run_process.py          # লিখন, মান নিয়ন্ত্রণ ও প্রকাশনা CLI
├── src/                        # Astro 5 + TypeScript + Tailwind CSS ফ্রন্টএন্ড
│   ├── components/             # Logo, Header, Footer, ArticleCard, CssIllustration, PeerReviewBanner...
│   ├── layouts/                # BaseLayout, ArticleLayout, ExplainerLayout
│   ├── lib/                    # বিভাগ, বাংলা তারিখ/সংখ্যা ফরম্যাটার, URL base-path ও JSON-LD হেল্পার
│   ├── pages/                  # সকল পেজ, ডায়নামিক রুট, সার্চ, ৪০৪, RSS/Atom ও robots.txt
│   ├── styles/                 # গ্লোবাল টাইপোগ্রাফি ও সম্পাদকীয় স্টাইলশিট
│   └── content.config.ts       # Astro Content Layer ও Zod ভ্যালিডেশন স্কিমা
├── tests/                      # স্বয়ংক্রিয় পরীক্ষা স্যুট
│   ├── frontend/verify_build.mjs
│   └── test_*.py
└── .github/workflows/          # SHA-পিনকৃত GitHub Actions ওয়ার্কফ্লো (collect, process, deploy, ci)
```

---

## ৩. লোকাল সেটআপ ও চালানোর নির্দেশাবলি (Local Setup & Commands)

### পূর্বশর্ত
- **Node.js** `>= 20` (প্রস্তাবিত: Node.js `22 LTS`) এবং `npm`
- **Python** `3.12` (Python `3.11+` লোকালে সমর্থিত; প্রোডাকশন CI-তে Python `3.12` ব্যবহৃত)

### ধাপ ১: এনভায়রনমেন্ট ফাইল প্রস্তুত করুন
```bash
cp .env.example .env
```
*(Windows PowerShell-এ: `Copy-Item .env.example .env`)*

### ধাপ ২: ফ্রন্টএন্ড ইনস্টল, ডেভেলপমেন্ট ও প্রোডাকশন বিল্ড
```bash
# ১. ডিপেন্ডেন্সি ইনস্টল
npm install

# ২. লোকাল ডেভেলপমেন্ট সার্ভার (http://localhost:4321)
npm run dev

# ৩. TypeScript ও Astro Content Schema যাচাই
npm run check

# ৪. প্রোডাকশন স্ট্যাটিক বিল্ড + Pagefind বাংলা/ইংরেজি সার্চ ইনডেক্স তৈরি
npm run build

# ৫. প্রোডাকশন বিল্ড প্রিভিউ
npm run preview
```

### ধাপ ৩: Python অটোমেশন ইঞ্জিন সেটআপ ও চালানো
```bash
# ভার্চুয়াল এনভায়রনমেন্ট তৈরি ও সক্রিয়করণ (ঐচ্ছিক কিন্তু প্রস্তাবিত)
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

# গবেষণা মেটাডেটা সংগ্রহ (লাইভ নেটওয়ার্ক সংযোগ প্রয়োজন)
python scripts/run_collect.py --max-per-source 5

# সংগৃহীত মেটাডেটা থেকে নিবন্ধ তৈরি ও QC যাচাই (Dry-run মোডে পরীক্ষা)
python scripts/run_process.py --dry-run
```

---

## ৪. স্বয়ংক্রিয় পরীক্ষা চালানো (Running Tests)

```bash
# ১. Python ইউনিট টেস্ট (কালেক্টর, ডিডুপ্লিকেশন, লাইসেন্স, QC গেট, স্কিমা ও GitHub Actions নিরাপত্তা)
python -m pytest -v

# ২. ফ্রন্টএন্ড বিল্ড, রুট/সাব-পাথ লিংক যাচাই, JSON-LD এবং প্রিপ্রিন্ট সুরক্ষা পরীক্ষা
npm test
```

---

## ৫. প্রয়োজনীয় GitHub Secrets ও বাহ্যিক কনফিগারেশন (External Configuration)

> **স্বচ্ছতা নোট:** এই রিপোজিটরিতে কোনো API কী বা বাহ্যিক লাইভ ডিপ্লয়মেন্ট সংযুক্ত বলে দাবি করা হয়নি। স্বয়ংক্রিয় AI লিখন এবং GitHub Pages ডিপ্লয়মেন্ট সক্রিয় করতে রিপোজিটরির মালিককে নিচের সেটিংস কনফিগার করতে হবে।

### A. GitHub Repository Secrets (`Settings → Secrets and variables → Actions → Secrets`)

| Secret নাম | আবশ্যিক? | বিবরণ |
| :--- | :---: | :--- |
| `AI_PROVIDER` | হ্যাঁ (প্রোডাকশনে) | `gemini`, `openai`, `openai_compatible`, অথবা `anthropic`। কনফিগার না করলে ডিফল্ট `mock` থাকে (যা কেবল `REVIEW` কিউতে রাখে, কখনোই স্বয়ংক্রিয় প্রকাশ করে না)। |
| `AI_API_KEY` | হ্যাঁ (লাইভ AI-এ) | নির্বাচিত AI প্রোভাইডারের API Key। |
| `AI_MODEL` | ঐচ্ছিক | যেমন: `gemini-2.5-flash`, `gpt-4o-mini`, অথবা `claude-3-5-haiku-latest`। |
| `AI_BASE_URL` | ঐচ্ছিক | কাস্টম OpenAI-compatible এন্ডপয়েন্ট ব্যবহারের ক্ষেত্রে বেস URL। |
| `PIPELINE_CONTACT_EMAIL` | প্রস্তাবিত | Crossref Polite Pool এবং NCBI PubMed E-utilities নীতিমালা অনুযায়ী যোগাযোগের ইমেইল। |
| `NCBI_API_KEY` | ঐচ্ছিক | PubMed এপিআই-এ উচ্চতর রেট-লিমিটের জন্য। |
| `PLOS_API_KEY` | ঐচ্ছিক | PLOS API কী (প্রয়োজন হলে)। |

### B. GitHub Repository Variables (`Settings → Secrets and variables → Actions → Variables`)

| Variable নাম | উদাহরণ (কাস্টম ডোমেইন) | উদাহরণ (প্রজেক্ট সাব-পাথ) | বিবরণ |
| :--- | :--- | :--- | :--- |
| `SITE_URL` | `https://biobangla.org` | `https://<username>.github.io` | ক্যানোনিকাল URL, RSS ও Sitemap তৈরির মূল ডোমেইন। |
| `BASE_PATH` | `/` | `/biobangla` | প্রজেক্ট রিপোজিটরি সাব-পাথে হোস্ট করলে রিপোজিটরির নাম দিন। |

### C. GitHub Pages সক্রিয়করণ (`Settings → Pages`)
1. GitHub রিপোজিটরির **Settings → Pages** অংশে যান।
2. **Build and deployment → Source** হিসেবে **GitHub Actions** নির্বাচন করুন।
3. কাস্টম ডোমেইন ব্যবহার করতে চাইলে `public/CNAME.example` ফাইলটি কপি করে `public/CNAME` নামে সংরক্ষণ করুন এবং আপনার ডোমেইনের DNS-এ GitHub Pages রেকর্ড যুক্ত করুন।

---

## ৬. মান নিয়ন্ত্রণ গেট (`PASS` / `REVIEW` / `FAIL`)

প্রকাশের পূর্বে `scripts/ai/validator.py` প্রতিটি খসড়া নিবন্ধের ওপর স্বাধীন নিরীক্ষা চালায়:
- **`PASS`:** বৈধ HTTPS উৎস, সঠিক DOI, ডুপ্লিকেটমুক্ত, প্রিপ্রিন্ট ও লাইসেন্স নীতিমালা উত্তীর্ণ, যথাযথ বাংলা অনুপাত, ৫টি আবশ্যিক অনুচ্ছেদ উপস্থিত এবং কোনো চিকিৎসা পরামর্শ নেই — কেবল তখনই `content/articles/`-এ প্রকাশিত হয়।
- **`REVIEW`:** মানব সম্পাদকের পরিদর্শন প্রয়োজন (যেমন: DOI অনুপস্থিত, সংক্ষিপ্ত নিবন্ধ, অতিরঞ্জিত বিশেষণ, অথবা `mock` প্রোভাইডার) — `state/review_queue/`-তে সংরক্ষিত থাকে।
- **`FAIL`:** ডুপ্লিকেট নিবন্ধ, ত্রুটিপূর্ণ বা কাল্পনিক DOI, কপিরাইটযুক্ত প্রকাশকের ছবি ব্যবহার, প্রিপ্রিন্টকে পিয়ার-রিভিউকৃত দাবি করা, অথবা চিকিৎসা পরামর্শ প্রদান — তাৎক্ষণিকভাবে বাতিল।

---

## ৭. লাইসেন্স ও দায়মুক্তি
- প্ল্যাটফর্মের সোর্স কোড এবং মৌলিক বাংলা শিক্ষামূলক ব্যাখ্যা অবাণিজ্যিক শিক্ষামূলক উদ্দেশ্যে রচিত; প্রতিটি উদ্ধৃত গবেষণাপত্রের স্বত্ব ও লাইসেন্স মূল লেখক ও প্রকাশকের নিকট সংরক্ষিত।
- **চিকিৎসা দায়মুক্তি:** জীববিজ্ঞান (`biobangla`)-এ প্রকাশিত কোনো নিবন্ধ চিকিৎসা পরামর্শ বা রোগ নির্ণয়ের বিকল্প নয়।
