# 🛡️ RugRadar

An AI-powered rug pull detector for Solana tokens. Before you ape in, let RugRadar scan the token and give you a **Trust Score** based on real on-chain data.

**Built by LixerDev**

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Solana](https://img.shields.io/badge/network-Solana-9945FF)
![License](https://img.shields.io/badge/license-MIT-purple)

---

## 🔍 What Does RugRadar Check?

RugRadar runs **9 independent checks** on any Solana token and synthesizes them into a **0-100 Trust Score** using GPT-4.

| # | Check | Why It Matters |
|---|---|---|
| 1 | **Mint Authority** | If active, creator can print unlimited tokens → instant dump |
| 2 | **Freeze Authority** | If active, creator can freeze your wallet → you can't sell |
| 3 | **Holder Concentration** | Top 10 holders owning >60% = coordinated dump risk |
| 4 | **Creator History** | Has this wallet rugged before? How many tokens created? |
| 5 | **Liquidity Status** | Is LP locked or burned? Unlocked LP = easy rug |
| 6 | **Bundle Detection** | Did multiple wallets buy in the same block? Classic manipulation |
| 7 | **Social Verification** | Are Twitter/Telegram/website real and active? |
| 8 | **Token Age & Metadata** | New token with no history = higher risk |
| 9 | **AI Synthesis** | GPT combines all signals into a final verdict |

---

## 🚀 Quick Start

```bash
git clone https://github.com/LixerDev/RugRadar.git
cd RugRadar
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env

# Scan a single token
python main.py scan <MINT_ADDRESS>

# Scan and export JSON report
python main.py scan <MINT_ADDRESS> --output report.json

# Watch mode: scan every new PumpFun launch automatically
python main.py watch

# View scan history
python main.py history
```

---

## 📊 Example Output

```
┌─────────────────────────────────────────────────────┐
│  🛡️  RugRadar Report — $PEPE2 (EPE...k7Xd)          │
├─────────────────────────────────────────────────────┤
│  Trust Score     │  23 / 100     ❌ HIGH RISK        │
│  Verdict         │  LIKELY RUG                       │
├─────────────────────────────────────────────────────┤
│  Mint Authority  │  ❌ ACTIVE — creator can mint     │
│  Freeze Auth     │  ❌ ACTIVE — can freeze wallets   │
│  Top 10 Holders  │  ⚠️  87% concentration            │
│  Creator History │  ❌ 3 abandoned tokens found      │
│  Liquidity       │  ⚠️  Not locked                   │
│  Bundling        │  ❌ 12 wallets bought same block  │
│  Socials         │  ⚠️  Twitter unverified           │
│  Token Age       │  ⚠️  4 minutes old               │
├─────────────────────────────────────────────────────┤
│  AI Analysis     │  Multiple critical red flags.     │
│                  │  Creator wallet has rugged 3x.    │
│                  │  Bundle activity suggests insider │
│                  │  coordination. Avoid.             │
└─────────────────────────────────────────────────────┘
```

---

## ⚙️ Configuration

Copy `.env.example` → `.env` and fill in:

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | For AI Trust Score synthesis | ✅ |
| `SOLANA_RPC_URL` | Solana RPC (Helius recommended for speed) | ✅ |
| `HELIUS_API_KEY` | Helius API for enhanced token data | Optional |
| `BIRDEYE_API_KEY` | Birdeye for holder/liquidity data | Optional |

> **Tip:** Free public RPCs work but are slow. Use [Helius](https://helius.dev) for best results.

---

## 🏗️ Architecture

```
main.py (CLI)
    └── Analyzer (orchestrator)
            ├── ChainScanner    → Solana RPC calls (mint auth, freeze auth, holders)
            ├── CreatorChecker  → Creator wallet transaction history
            ├── BundleDetector  → Same-block buy pattern detection
            ├── SocialChecker   → HTTP checks on Twitter/Telegram/website
            ├── AIScorer        → GPT synthesizes all signals
            └── Reporter        → Terminal output + JSON export
```

---

## ⚠️ Disclaimer

> RugRadar is a research tool and does **not** constitute financial advice. No tool can guarantee 100% rug pull detection. Always DYOR. Never invest more than you can afford to lose.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
