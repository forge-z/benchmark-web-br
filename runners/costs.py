"""Public list prices copied on 2026-11-18. Estimates, not an invoice.

Sources:
- https://exa.ai/docs/admin/pricing
- https://docs.parallel.ai/getting-started/pricing
- https://docs.tinyfish.ai/search-api and https://docs.tinyfish.ai/fetch-api
- https://docs.firecrawl.dev/billing
- https://docs.context.dev/skill.md (credit table)
"""

from __future__ import annotations

# Exa: /search type auto, up to 10 results. Highlights on /contents are
# US$ 1 / 1,000 pages per content type. Search highlights are estimated the same way.
EXA_SEARCH_AUTO_USD = 7 / 1000
EXA_CONTENTS_TEXT_USD = 1 / 1000

# Parallel /v1 list prices. Search omits mode, so the documented default is advanced.
# Extract is US$ 1 / 1,000 URLs. Task core is US$ 25 / 1,000 successful runs.
PARALLEL_SEARCH_CEILING_USD = 5 / 1000
PARALLEL_EXTRACT_USD = 1 / 1000
PARALLEL_TASK_CORE_USD = 25 / 1000

# TinyFish documents a free daily allowance, not a per-call price inside it.
TINYFISH_SEARCH_FREE_PER_DAY = 12000
TINYFISH_FETCH_FREE_URLS_PER_DAY = 1000

# Firecrawl credits, from the public billing page.
FIRECRAWL_SEARCH_CREDITS_PER_10 = 2
FIRECRAWL_SCRAPE_CREDITS = 1
# JSON format on /scrape is +4 credits per page, on top of the 1-credit scrape.
FIRECRAWL_SCRAPE_JSON_CREDITS = 5

# Context.dev credits. The public page does not convert a credit to USD.
CONTEXT_NEWS_CREDITS_PER_10 = 1
CONTEXT_WEB_SEARCH_CREDITS_PER_10 = 1
CONTEXT_SCRAPE_CREDITS = 1
CONTEXT_COMPANY_SEARCH_FAST_CREDITS = 2
