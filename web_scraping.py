import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

# File to store the last scraped timestamp
last_scraped_file = 'last_scraped_timestamp.txt'

def get_last_scraped_timestamp():
    """Get the last scraped timestamp from the file."""
    try:
        with open(last_scraped_file, 'r') as file:
            return datetime.strptime(file.read().strip(), '%Y-%m-%d %H:%M:%S')
    except FileNotFoundError:
        # If the file does not exist, return a very old datetime
        return datetime(1970, 1, 1)

def update_last_scraped_timestamp(timestamp):
    """Update the last scraped timestamp in the file."""
    with open(last_scraped_file, 'w') as file:
        file.write(timestamp.strftime('%Y-%m-%d %H:%M:%S'))

def scrape_album_list(url):
    """Scrape the album list from the given URL."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    album_list = soup.find_all('td', class_='details')
    
    albums = []
    for album in album_list:
        link = album.find('a', class_='title', href=True)
        artist = album.find('div', class_='artist').get_text(strip=True)
        date_str = album.find('span').get_text(strip=True)
        release_date = datetime.strptime(date_str, '%B %d, %Y')
        
        if link:
            albums.append({
                'url': f"https://www.metacritic.com{link['href']}",
                'title': link.get_text(strip=True),
                'artist': artist,
                'release_date': release_date
            })
    
    # Find the next page URL
    next_page = soup.find('span', class_='flipper next')
    next_page_url = None
    if next_page and next_page.find('a', href=True):
        next_page_url = f"https://www.metacritic.com{next_page.find('a')['href']}"
    
    return albums, next_page_url

def scrape_album_reviews(album_url):
    """Scrape reviews from the album page."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(album_url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    review_section = soup.find_all('div', class_='review')
    
    reviews = []
    for review in review_section:
        publication = review.find('div', class_='source').get_text(strip=True)
        score = review.find('div', class_='metascore_w').get_text(strip=True)
        quote = review.find('div', class_='review_body').get_text(strip=True)
        date = review.find('div', class_='date').get_text(strip=True)
        
        reviews.append({
            'Publication': publication,
            'Score': score,
            'Quote': quote,
            'Date': date
        })
    
    return reviews

def main():
    base_url = 'https://www.metacritic.com/browse/albums/release-date/available/date?view=condensed'
    
    last_scraped_timestamp = get_last_scraped_timestamp()
    print(f"Last scraped timestamp: {last_scraped_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_albums = []
    current_url = base_url
    
    while current_url:
        albums, next_page_url = scrape_album_list(current_url)
        all_albums.extend(albums)
        current_url = next_page_url
        print(f"Scraped {len(albums)} albums from {current_url}")
    
    new_reviews = []
    for album in all_albums:
        # Check if the album release date is after the last scraped timestamp
        if album['release_date'] > last_scraped_timestamp:
            print(f"Scraping {album['url']} (released on {album['release_date'].strftime('%Y-%m-%d')})")
            reviews = scrape_album_reviews(album['url'])
            for review in reviews:
                review.update({
                    'Album': album['title'],
                    'Artist': album['artist'],
                    'Release Date': album['release_date'].strftime('%Y-%m-%d')
                })
            new_reviews.extend(reviews)
    
    if new_reviews:
        # Update the last scraped timestamp to the current time
        latest_timestamp = datetime.now()
        update_last_scraped_timestamp(latest_timestamp)
        
        # Create a DataFrame from the reviews
        df = pd.DataFrame(new_reviews)
        
        # Save to a CSV file
        csv_file = 'metacritic_album_reviews.csv'
        df.to_csv(csv_file, mode='a', header=not pd.read_csv(csv_file).empty, index=False)
        
        print(f"New reviews added to {csv_file}")
    else:
        print("No new reviews to add.")

if __name__ == '__main__':
    main()
