# Embodied Intelligence Radar

Chinese-language daily dashboard for embodied AI and robotics industry intelligence.

## Features
- Responsive Chinese dashboard for news, technology, companies, jobs, conferences, interviews and deployments.
- Curated starter stories with publication dates, source names, source links and evidence labels.
- Daily RSS discovery and arXiv paper collection.
- GitHub Actions workflow scheduled for 08:15 China Standard Time.

## Install into the existing portfolio
Copy this folder to `embodied-radar/` in the root of the existing `wangqiuna-portfolio` repository. Copy the workflow from the install package's `.github/workflows/daily-update.yml` to the repository root at `.github/workflows/daily-update.yml`. Do not modify the separate `ai-chinese-daily` repository.

## Accuracy and coverage
RSS is a discovery layer, not independent fact-checking. The site preserves publication dates and original source links. Source-provided snippets are not rewritten as verified facts. Preprints are labeled as preprints. Company announcements, demos, pilot tests, announced orders, deliveries and customer-accepted deployments are distinct evidence classes.

Public job-board coverage is incomplete because many platforms require login or restrict automated feeds. The current pipeline searches public RSS/news signals for hiring; add official company career pages or curated job URLs for stronger coverage. GitHub Actions schedules can be delayed by platform load.
