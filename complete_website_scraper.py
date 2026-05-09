# mera complete website scraper 
# internship task 1 ke liye bana raha hoon
# ye poore website ka saara data lega

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime
import json

# ----------------------------
# config settings
# ----------------------------
BASE_SITE = "https://books.toscrape.com/"
DELAY_BETWEEN_REQUESTS = 0.5  # thoda wait karna nahi toh website block kar degi
MAX_RETRIES = 3  # agar fail ho jaye toh dobaara try karna

# global list jahan saara data store hoga
complete_dataset = []

# ----------------------------
# ye function har ek product ka link collect karega
# ----------------------------
def get_all_product_links():
    """
    saare products ke links collect karta hai
    maine manually check kiya website mein 50 pages hain
    """
    all_links = []
    page_num = 1
    
    print("\n" + "="*60)
    print("STEP 1: COLLECTING ALL PRODUCT LINKS")
    print("="*60)
    
    while True:
        print(f"checking page {page_num} for products...")
        
        # ab page ka url banao
        if page_num == 1:
            page_url = "https://books.toscrape.com/catalogue/page-1.html"
        else:
            page_url = f"https://books.toscrape.com/catalogue/page-{page_num}.html"
        
        # request bhejo
        try:
            response = requests.get(page_url)
            print(f"  status: {response.status_code}")
        except:
            print(f"  error on page {page_num}, stopping")
            break
        
        if response.status_code != 200:
            print("  page not found, yahi last page hai")
            break
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # saare books dhundo is page mein
        books = soup.find_all("article", class_="product_pod")
        
        if len(books) == 0:
            print("  koi product nahi mila is page mein")
            break
        
        print(f"  mil gaye {len(books)} products is page mein")
        
        # har book ka link nikal lo
        for book in books:
            # link extract karo
            link_tag = book.find("h3").find("a")
            relative_link = link_tag["href"]
            
            # relative link ko absolute mein convert karo
            # pehle extra 'catalogue/' hatao agar hai toh
            if relative_link.startswith("../"):
                relative_link = relative_link[3:]
            
            full_link = f"https://books.toscrape.com/catalogue/{relative_link}"
            all_links.append(full_link)
        
        # check karo next page hai ya nahi
        next_btn = soup.find("li", class_="next")
        if next_btn is None:
            print(f"  ye last page tha ({page_num})")
            break
        
        page_num += 1
        time.sleep(0.3)  # thoda wait karo
    
    print(f"\n✅ TOTAL PRODUCTS FOUND: {len(all_links)}")
    return all_links

# ----------------------------
# ye function har product ki sari details nikalega
# ----------------------------
def scrape_complete_product_details(product_url, product_index, total_products):
    """
    ek product ke page se saari information extract karta hai
    maine try kiya maximum fields collect karne ka
    """
    
    print(f"  scraping {product_index}/{total_products}...", end=" ")
    
    # retry logic agar request fail ho jaye
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(product_url)
            if response.status_code == 200:
                break
        except:
            if attempt == MAX_RETRIES - 1:
                print("failed after retries")
                return None
            time.sleep(1)
    
    if response.status_code != 200:
        print(f"http error {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.content, "html.parser")
    
    # -------------------------------------------------
    # AB MAINE SAARE FIELDS EXTRACT KARNE KI KOSHISH KI HAI
    # -------------------------------------------------
    
    product_data = {}
    
    # 1. BASIC INFORMATION
    # --------------------------------------
    try:
        title_tag = soup.find("h1")
        product_data["product_title"] = title_tag.text.strip() if title_tag else "not_found"
    except:
        product_data["product_title"] = "error_extracting"
    
    # 2. PRICE INFORMATION
    # --------------------------------------
    try:
        price_tag = soup.find("p", class_="price_color")
        product_data["current_price"] = price_tag.text.strip() if price_tag else "not_found"
    except:
        product_data["current_price"] = "error"
    
    # original price agar sale ho rahi hai toh
    try:
        old_price_tag = soup.find("p", class_="old_price")
        product_data["original_price"] = old_price_tag.text.strip() if old_price_tag else "no_discount"
    except:
        product_data["original_price"] = "no_discount"
    
    # 3. TAX (kuch books pe tax hota hai)
    # --------------------------------------
    try:
        tax_tag = soup.find("th", string="Tax")
        if tax_tag:
            tax_value = tax_tag.find_next("td").text
            product_data["tax"] = tax_value
        else:
            product_data["tax"] = "not_applicable"
    except:
        product_data["tax"] = "unknown"
    
    # 4. RATING (1 se 5 stars)
    # --------------------------------------
    try:
        rating_stars = soup.find("p", class_="star-rating")
        if rating_stars:
            rating_class = rating_stars["class"][1]
            rating_map = {
                "One": 1, "Two": 2, "Three": 3, 
                "Four": 4, "Five": 5
            }
            product_data["rating_stars"] = rating_map.get(rating_class, 0)
        else:
            product_data["rating_stars"] = 0
    except:
        product_data["rating_stars"] = 0
    
    # 5. AVAILABILITY AND STOCK COUNT
    # --------------------------------------
    try:
        availability_div = soup.find("p", class_="instock availability")
        if availability_div:
            stock_text = availability_div.text.strip()
            # regex se numbers nikalna
            stock_numbers = re.findall(r'\d+', stock_text)
            if stock_numbers:
                product_data["stock_quantity"] = int(stock_numbers[0])
            else:
                product_data["stock_quantity"] = 0
            product_data["availability_status"] = "in_stock"
        else:
            product_data["stock_quantity"] = 0
            product_data["availability_status"] = "unknown"
    except:
        product_data["stock_quantity"] = 0
        product_data["availability_status"] = "error"
    
    # 6. PRODUCT DESCRIPTION
    # --------------------------------------
    try:
        desc_div = soup.find("div", id="product_description")
        if desc_div:
            desc_paragraph = desc_div.find_next("p")
            product_data["product_description"] = desc_paragraph.text.strip() if desc_paragraph else ""
        else:
            product_data["product_description"] = ""
    except:
        product_data["product_description"] = ""
    
    # 7. UPC CODE (universal product code)
    # --------------------------------------
    try:
        upc_th = soup.find("th", string="UPC")
        if upc_th:
            upc_td = upc_th.find_next("td")
            product_data["upc_code"] = upc_td.text.strip() if upc_td else "not_found"
        else:
            product_data["upc_code"] = "not_found"
    except:
        product_data["upc_code"] = "error"
    
    # 8. PRODUCT TYPE
    # --------------------------------------
    try:
        type_th = soup.find("th", string="Product Type")
        if type_th:
            type_td = type_th.find_next("td")
            product_data["product_type"] = type_td.text.strip() if type_td else "unknown"
        else:
            product_data["product_type"] = "unknown"
    except:
        product_data["product_type"] = "error"
    
    # 9. NUMBER OF REVIEWS
    # --------------------------------------
    try:
        reviews_th = soup.find("th", string="Number of reviews")
        if reviews_th:
            reviews_td = reviews_th.find_next("td")
            product_data["num_reviews"] = int(reviews_td.text.strip()) if reviews_td else 0
        else:
            product_data["num_reviews"] = 0
    except:
        product_data["num_reviews"] = 0
    
    # 10. CATEGORY (breadcrumb se nikalna)
    # --------------------------------------
    try:
        breadcrumb_ul = soup.find("ul", class_="breadcrumb")
        if breadcrumb_ul:
            breadcrumb_items = breadcrumb_ul.find_all("li")
            if len(breadcrumb_items) >= 3:
                product_data["category"] = breadcrumb_items[2].text.strip()
            elif len(breadcrumb_items) >= 2:
                product_data["category"] = breadcrumb_items[1].text.strip()
            else:
                product_data["category"] = "unknown"
        else:
            product_data["category"] = "unknown"
    except:
        product_data["category"] = "error"
    
    # 11. IMAGE URL
    # --------------------------------------
    try:
        image_div = soup.find("div", class_="item active")
        if image_div:
            img_tag = image_div.find("img")
            if img_tag and img_tag.get("src"):
                img_src = img_tag["src"]
                # relative se absolute url banao
                if img_src.startswith("../"):
                    img_src = img_src[3:]
                product_data["image_url"] = f"https://books.toscrape.com/{img_src}"
            else:
                product_data["image_url"] = "not_found"
        else:
            product_data["image_url"] = "not_found"
    except:
        product_data["image_url"] = "error"
    
    # 12. PRODUCT URL (for reference)
    # --------------------------------------
    product_data["product_url"] = product_url
    
    # 13. PAGE NUMBER (jahan mila)
    # --------------------------------------
    # ye baad mein set karunga, abhi ke liye placeholder
    product_data["page_found"] = "unknown"
    
    print("done")
    return product_data

# ----------------------------
# ye main function hai jo sab kuch run karega
# ----------------------------
def scrape_entire_website():
    
    print("\n" + "="*60)
    print("🚀 STARTING COMPLETE WEBSITE SCRAPE")
    print("="*60)
    print(f"start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # STEP 1: pehle saare links collect karte hain
    all_product_links = get_all_product_links()
    
    if len(all_product_links) == 0:
        print("\n❌ ERROR: Koi product link nahi mila!")
        return []
    
    # STEP 2: ab har product ki details scrape karte hain
    print("\n" + "="*60)
    print("STEP 2: EXTRACTING COMPLETE PRODUCT DETAILS")
    print("="*60)
    print(f"total products to scrape: {len(all_product_links)}")
    print("ye thoda time lega, please wait...\n")
    
    scraped_data = []
    failed_products = []
    
    for idx, link in enumerate(all_product_links, 1):
        product_details = scrape_complete_product_details(link, idx, len(all_product_links))
        
        if product_details:
            # page number add karo
            # page number extract kar raha hoon url se
            page_match = re.search(r'page-(\d+)', link)
            if page_match:
                product_details["page_found"] = int(page_match.group(1))
            else:
                product_details["page_found"] = 1
            
            scraped_data.append(product_details)
        else:
            failed_products.append(link)
        
        # har 20 products ke baad progress save karta hoon
        if idx % 20 == 0:
            print(f"\n  [PROGRESS SAVED] {idx}/{len(all_product_links)} products done")
            temp_df = pd.DataFrame(scraped_data)
            temp_df.to_csv(f"temp_progress_{datetime.now().strftime('%H%M%S')}.csv", index=False)
        
        # website pe load kam karne ke liye delay
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    print("\n" + "="*60)
    print("SCRAPING COMPLETED!")
    print("="*60)
    print(f"✅ successfully scraped: {len(scraped_data)} products")
    print(f"❌ failed: {len(failed_products)} products")
    
    if failed_products:
        print("\nfailed product links:")
        for link in failed_products[:10]:  # sirf 10 dikhao
            print(f"  - {link}")
    
    return scraped_data

# ----------------------------
# save data in multiple formats
# ----------------------------
def save_all_formats(data, df):
    """
    data ko alag alag formats mein save karta hai
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("\n" + "="*60)
    print("SAVING DATA IN MULTIPLE FORMATS")
    print("="*60)
    
    # 1. CSV format
    csv_file = f"complete_website_data_{timestamp}.csv"
    df.to_csv(csv_file, index=False)
    print(f"✅ CSV saved: {csv_file}")
    
    # 2. Excel format
    excel_file = f"complete_website_data_{timestamp}.xlsx"
    df.to_excel(excel_file, index=False)
    print(f"✅ Excel saved: {excel_file}")
    
    # 3. JSON format
    json_file = f"complete_website_data_{timestamp}.json"
    df.to_json(json_file, orient="records", indent=2)
    print(f"✅ JSON saved: {json_file}")
    
    # 4. SQLite database
    import sqlite3
    db_file = f"ecommerce_data_{timestamp}.db"
    conn = sqlite3.connect(db_file)
    df.to_sql("products", conn, if_exists="replace", index=False)
    conn.close()
    print(f"✅ SQLite database saved: {db_file}")
    
    return csv_file, excel_file, json_file, db_file

# ----------------------------
# analysis and statistics
# ----------------------------
def generate_full_report(df):
    """
    scraped data ka analysis karta hai
    """
    print("\n" + "="*60)
    print("📊 COMPLETE DATA ANALYSIS REPORT")
    print("="*60)
    
    # basic stats
    print(f"\n📌 OVERALL STATISTICS:")
    print(f"   Total Products: {len(df)}")
    print(f"   Total Categories: {df['category'].nunique()}")
    print(f"   Average Rating: {df['rating_stars'].mean():.2f}/5")
    print(f"   Total Reviews: {df['num_reviews'].sum():,}")
    print(f"   Total Stock Available: {df['stock_quantity'].sum():,}")
    
    # price analysis - careful with £ sign
    try:
        df['price_numeric'] = df['current_price'].str.replace('£', '').astype(float)
        print(f"\n💰 PRICE ANALYSIS:")
        print(f"   Average Price: £{df['price_numeric'].mean():.2f}")
        print(f"   Min Price: £{df['price_numeric'].min():.2f}")
        print(f"   Max Price: £{df['price_numeric'].max():.2f}")
        print(f"   Median Price: £{df['price_numeric'].median():.2f}")
    except:
        print("   Price analysis: error processing prices")
    
    # rating distribution
    print(f"\n⭐ RATING DISTRIBUTION:")
    rating_counts = df['rating_stars'].value_counts().sort_index()
    for rating, count in rating_counts.items():
        percentage = (count/len(df))*100
        bar = "█" * int(percentage/2)
        print(f"   {rating} stars: {count:3d} products ({percentage:5.1f}%) {bar}")
    
    # top categories
    print(f"\n📚 TOP 10 CATEGORIES:")
    category_counts = df['category'].value_counts().head(10)
    for cat, count in category_counts.items():
        print(f"   {cat:<25}: {count:3d} products")
    
    # stock analysis
    print(f"\n📦 STOCK ANALYSIS:")
    in_stock = df[df['stock_quantity'] > 0].shape[0]
    out_stock = df[df['stock_quantity'] == 0].shape[0]
    print(f"   In Stock: {in_stock} products")
    print(f"   Out of Stock: {out_stock} products")
    
    # best sellers by reviews
    print(f"\n🏆 TOP 10 MOST REVIEWED PRODUCTS:")
    top_reviewed = df.nlargest(10, 'num_reviews')[['product_title', 'num_reviews', 'rating_stars', 'current_price']]
    for idx, row in top_reviewed.iterrows():
        title_short = row['product_title'][:45] + "..." if len(row['product_title']) > 45 else row['product_title']
        print(f"   {title_short:<48} | {row['num_reviews']:3d} reviews | ⭐{row['rating_stars']}")
    
    # highest rated (with minimum 10 reviews)
    print(f"\n⭐ HIGHEST RATED PRODUCTS (min 10 reviews):")
    high_rated = df[df['num_reviews'] >= 10].nlargest(10, 'rating_stars')[['product_title', 'rating_stars', 'num_reviews', 'current_price']]
    for idx, row in high_rated.iterrows():
        title_short = row['product_title'][:45] + "..." if len(row['product_title']) > 45 else row['product_title']
        print(f"   {title_short:<48} | ⭐{row['rating_stars']} | {row['num_reviews']} reviews")
    
    return rating_counts, category_counts

# ----------------------------
# main execution
# ----------------------------
if __name__ == "__main__":
    
    print("\n")
    print("🐍 PYTHON WEB SCRAPER - COMPLETE WEBSITE")
    print("   CodeAlpha Internship Task 1")
    print("   Made by: [Your Name]")
    print("   Date: " + datetime.now().strftime("%B %d, %Y"))
    
    # run the scraper
    scraped_data = scrape_entire_website()
    
    if len(scraped_data) > 0:
        # convert to dataframe
        df = pd.DataFrame(scraped_data)
        
        # save in all formats
        csv_file, excel_file, json_file, db_file = save_all_formats(scraped_data, df)
        
        # generate report
        generate_full_report(df)
        
        # preview data
        print("\n" + "="*60)
        print("DATA PREVIEW (first 5 rows)")
        print("="*60)
        print(df.head())
        
        print("\n" + "="*60)
        print("✅ ALL TASKS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\n📁 Output files created:")
        print(f"   - {csv_file}")
        print(f"   - {excel_file}")
        print(f"   - {json_file}")
        print(f"   - {db_file}")
        
        print("\n📊 Data Summary:")
        print(f"   {len(scraped_data)} rows × {len(df.columns)} columns")
        print("\n📋 Columns extracted:")
        for col in df.columns:
            print(f"   • {col}")
        
        print("\n🎯 READY FOR SUBMISSION!")
        print("   Don't forget to upload to GitHub and create LinkedIn video")
        
    else:
        print("\n❌ SCRAPING FAILED! Kuch bhi data nahi mila.")
        print("   Check your internet connection and try again.")
    
    print("\n" + "="*60)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")