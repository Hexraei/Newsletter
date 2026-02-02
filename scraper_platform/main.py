"""
Main Scraper Orchestrator
Runs all scrapers and aggregates results for the newsletter.
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.excel_tracker import ExcelTracker
from src.scrapers.hackernews_scraper import HackerNewsScraper
from src.scrapers.reddit_scraper import RedditScraper
from src.scrapers.github_scraper import GitHubScraper
from src.scrapers.medium_scraper import MediumScraper
from src.scrapers.producthunt_scraper import ProductHuntScraper


class ScraperOrchestrator:
    """Orchestrates all scrapers and aggregates results."""
    
    def __init__(self):
        self.tracker = ExcelTracker()
        self.all_items = []
        self.stats = {}
        
    async def run_all(self, save_to_file: bool = True) -> Dict[str, Any]:
        """Run all scrapers and collect results."""
        print("\n" + "="*70)
        print("COLLEGE NEWSLETTER SCRAPER - FULL RUN")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 1. Hacker News
        print("\n[1/5] Scraping Hacker News...")
        try:
            async with HackerNewsScraper() as scraper:
                items = await scraper.scrape(limit=30)
                self.all_items.extend(items)
                self.stats['hackernews'] = len(items)
                print(f"  -> Got {len(items)} items")
        except Exception as e:
            print(f"  -> ERROR: {e}")
            self.stats['hackernews'] = 0
        
        # 2. Reddit
        print("\n[2/5] Scraping Reddit...")
        try:
            async with RedditScraper() as scraper:
                items = await scraper.scrape(
                    subreddits=['technology', 'programming', 'cscareerquestions', 'MachineLearning'],
                    limit=15
                )
                self.all_items.extend(items)
                self.stats['reddit'] = len(items)
                print(f"  -> Got {len(items)} items")
        except Exception as e:
            print(f"  -> ERROR: {e}")
            self.stats['reddit'] = 0
        
        # 3. GitHub
        print("\n[3/5] Scraping GitHub...")
        try:
            async with GitHubScraper() as scraper:
                items = await scraper.scrape(
                    languages=['Python', 'JavaScript', 'TypeScript', 'Go'],
                    limit=10
                )
                self.all_items.extend(items)
                self.stats['github'] = len(items)
                print(f"  -> Got {len(items)} items")
        except Exception as e:
            print(f"  -> ERROR: {e}")
            self.stats['github'] = 0
        
        # 4. Medium
        print("\n[4/5] Scraping Medium...")
        try:
            scraper = MediumScraper()
            items = await scraper.scrape(limit=10)
            self.all_items.extend(items)
            self.stats['medium'] = len(items)
            print(f"  -> Got {len(items)} items")
        except Exception as e:
            print(f"  -> ERROR: {e}")
            self.stats['medium'] = 0
        
        # 5. Product Hunt
        print("\n[5/5] Scraping Product Hunt...")
        try:
            scraper = ProductHuntScraper()
            items = await scraper.scrape(limit=15)
            self.all_items.extend(items)
            self.stats['producthunt'] = len(items)
            print(f"  -> Got {len(items)} items")
        except Exception as e:
            print(f"  -> ERROR: {e}")
            self.stats['producthunt'] = 0
        
        # Save to Excel
        if save_to_file:
            self._save_results()
        
        # Print summary
        self._print_summary()
        
        return {
            'total_items': len(self.all_items),
            'by_source': self.stats,
            'items': [item.to_dict() for item in self.all_items]
        }
    
    def _save_results(self):
        """Save results to Excel and JSON."""
        # Save to Excel
        self.tracker.add_scraped_items([item.to_dict() for item in self.all_items])
        
        # Save to JSON
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_path = f'data/scraped_{timestamp}.json'
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'scraped_at': datetime.now().isoformat(),
                'total_items': len(self.all_items),
                'by_source': self.stats,
                'items': [item.to_dict() for item in self.all_items]
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n  Results saved to:")
        print(f"    - data/scraper_tests.xlsx")
        print(f"    - {json_path}")
    
    def _print_summary(self):
        """Print summary of results."""
        print("\n" + "="*70)
        print("SCRAPING COMPLETE")
        print("="*70)
        print(f"\nTotal items collected: {len(self.all_items)}")
        print("\nBy source:")
        for source, count in self.stats.items():
            print(f"  - {source}: {count} items")
        
        # Top items by engagement
        print("\nTop items by engagement:")
        sorted_items = sorted(
            self.all_items,
            key=lambda x: sum(x.engagement.values()),
            reverse=True
        )[:5]
        
        for i, item in enumerate(sorted_items, 1):
            total_engagement = sum(item.engagement.values())
            print(f"\n  {i}. [{item.source}]")
            print(f"     {item.title[:70]}...")
            print(f"     Engagement: {total_engagement} | URL: {item.url[:60]}...")
        
        print("\n" + "="*70)


def generate_newsletter_summary(orchestrator: ScraperOrchestrator) -> str:
    """Generate a newsletter summary from scraped items."""
    items = orchestrator.all_items
    
    # Group by source
    by_source = {}
    for item in items:
        source = item.source.split(' - ')[0]  # Get base source name
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(item)
    
    summary = []
    summary.append("# Daily Tech Newsletter\n")
    summary.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    summary.append(f"Total stories: {len(items)}\n")
    summary.append("="*70 + "\n")
    
    # Top stories section
    summary.append("\n## Top Stories\n")
    top_items = sorted(items, key=lambda x: sum(x.engagement.values()), reverse=True)[:10]
    
    for item in top_items:
        summary.append(f"\n### {item.title}")
        summary.append(f"- **Source:** {item.source}")
        summary.append(f"- **Author:** {item.author}")
        summary.append(f"- **URL:** {item.url}")
        if item.engagement:
            eng_str = ", ".join([f"{k}: {v}" for k, v in item.engagement.items()])
            summary.append(f"- **Engagement:** {eng_str}")
        summary.append("")
    
    # By category
    summary.append("\n## By Source\n")
    for source, source_items in by_source.items():
        summary.append(f"\n### {source} ({len(source_items)} items)\n")
        for item in source_items[:3]:  # Top 3 per source
            summary.append(f"- [{item.title[:60]}...]({item.url})")
        summary.append("")
    
    return "\n".join(summary)


if __name__ == "__main__":
    async def main():
        orchestrator = ScraperOrchestrator()
        results = await orchestrator.run_all(save_to_file=True)
        
        # Generate newsletter summary
        print("\n\nGenerating newsletter summary...")
        newsletter = generate_newsletter_summary(orchestrator)
        
        # Save newsletter
        timestamp = datetime.now().strftime('%Y%m%d')
        newsletter_path = f'data/newsletter_{timestamp}.md'
        with open(newsletter_path, 'w', encoding='utf-8') as f:
            f.write(newsletter)
        
        print(f"Newsletter saved to: {newsletter_path}")
        print("\nPreview:")
        print("-" * 70)
        print(newsletter[:1500])
        print("...")
        print("-" * 70)
    
    asyncio.run(main())
