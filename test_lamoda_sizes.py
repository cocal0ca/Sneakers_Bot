"""
Script to test Lamoda scraper with size extraction.
Should run for ~3 products and print sizes.
"""

from lamoda_scraper import get_lamoda_discounts

if __name__ == "__main__":
    print("Testing Scraper with Size Extraction (Limit 1 page)...")
    deals = get_lamoda_discounts(max_pages=1)

    print(f"\nTotal Deals: {len(deals)}")

    # Print first 5 with sizes
    for i, deal in enumerate(deals[:5]):
        print(f"{i + 1}. {deal['title']}")
        print(f"   Sizes: {deal['sizes']}")
        print(f"   Link: {deal['link']}")
        print("-" * 30)
