// Extract all asset page URLs from the Fab library page
// Usage: After manually scrolling to load all items, paste this into the browser console

(function() {
  const links = document.querySelectorAll('a[href^="/listings/"]');
  const urls = Array.from(new Set(
    Array.from(links)
      .map(a => a.getAttribute('href'))
      .filter(Boolean)
      .map(href => 'https://www.fab.com' + href)
  ));
  
  console.log(`Found ${urls.length} unique asset URLs`);
  console.log(JSON.stringify(urls, null, 2));
  
  // Also copy to clipboard if available
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(JSON.stringify(urls, null, 2))
      .then(() => console.log('✓ URLs copied to clipboard'))
      .catch(err => console.warn('Could not copy to clipboard:', err));
  }
  
  return urls;
})();
