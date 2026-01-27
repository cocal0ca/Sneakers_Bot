from streetbeat_scraper import StreetBeatScraper
import json


def test_scraper():
    print("Testing StreetBeatScraper with Hybrid JSON+DOM approach...")
    scraper = StreetBeatScraper()
    try:
        deals = scraper.scrape(max_pages=1)
        print(f"Found {len(deals)} deals.")

        if deals:
            print("\n--- First Deal Sample ---")
            deal = deals[0]
            print(json.dumps(deal, indent=4, ensure_ascii=False))

            # Validation
            assert deal["title"], "Title is missing"
            assert deal["image_url"], "Image URL is missing"
            assert deal["price"], "Price is missing"
            assert deal["sizes"], "Sizes are missing"
            assert deal["link"], "Link is missing"
            print("\nSUCCESS: All required fields present in the first deal.")

            # Check for missing images in all deals
            missing_images = [d for d in deals if not d.get("image_url")]
            if missing_images:
                print(f"WARNING: {len(missing_images)} deals have no image.")
            else:
                print("All deals have images.")

            # Check for missing sizes
            missing_sizes = [d for d in deals if not d.get("sizes")]
            if missing_sizes:
                print(
                    f"WARNING: {len(missing_sizes)} deals have no sizes (Should be filtered out)."
                )

        else:
            print("FAILURE: No deals found.")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        pass


if __name__ == "__main__":
    test_scraper()
