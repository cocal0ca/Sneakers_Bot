from affiliate_manager import AffiliateManager
import urllib.parse


def test_affiliate_manager():
    print("Testing AffiliateManager...")

    # Mock configuration for testing
    mock_config = {
        "ShopA": {"type": "admitad", "base_url": "https://ad.admitad.com/g/123/?ulp="},
        "ShopB": {"type": "custom", "base_url": "https://mysite.com/r?to="},
        "ShopC": {
            # Empty config - should return original
            "base_url": ""
        },
    }

    manager = AffiliateManager(networks=mock_config)

    # Test Case 1: ShopA (Admitad)
    original_url = "https://shop-a.com/product/123"
    expected_encoded = urllib.parse.quote(original_url)
    expected_result = f"https://ad.admitad.com/g/123/?ulp={expected_encoded}"

    res = manager.convert_link(original_url, "ShopA")
    print(f"[ShopA] Original: {original_url}")
    print(f"[ShopA] Result:   {res}")

    assert res == expected_result, "ShopA conversion failed"

    # Test Case 2: ShopB (Custom)
    res_b = manager.convert_link(original_url, "ShopB")
    expected_b = f"https://mysite.com/r?to={expected_encoded}"
    print(f"[ShopB] Result:   {res_b}")
    assert res_b == expected_b, "ShopB conversion failed"

    # Test Case 3: ShopC (Empty config)
    res_c = manager.convert_link(original_url, "ShopC")
    print(f"[ShopC] Result:   {res_c}")
    assert res_c == original_url, "ShopC should return original url"

    # Test Case 4: Unknown Source
    res_d = manager.convert_link(original_url, "UnknownShop")
    print(f"[Unkn]  Result:   {res_d}")
    assert res_d == original_url, "Unknown source should return original url"

    print("\nSUCCESS: AffiliateManager logic works correctly.")


if __name__ == "__main__":
    test_affiliate_manager()
