"""
HTML templates for DealFinder UI.
"""

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>DealFinder - Find Best Deals</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 48px;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .header p {
            font-size: 18px;
            opacity: 0.9;
        }
        .search-box {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        .search-form {
            display: flex;
            gap: 10px;
        }
        .search-input {
            flex: 1;
            padding: 15px 20px;
            font-size: 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            outline: none;
            transition: border-color 0.3s;
        }
        .search-input:focus {
            border-color: #667eea;
        }
        .search-button {
            padding: 15px 40px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        .search-button:hover {
            background: #5568d3;
        }
        .search-button:active {
            transform: scale(0.98);
        }
        .results-container {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            min-height: 200px;
        }
        #results {
            display: block !important;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        .loading.active {
            display: block;
        }
        .spinner {
            border: 4px solid #f3f4f6;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .examples {
            margin-top: 20px;
            text-align: center;
        }
        .examples span {
            display: inline-block;
            background: #edf2f7;
            padding: 6px 12px;
            margin: 4px;
            border-radius: 6px;
            font-size: 14px;
            color: #4a5568;
            cursor: pointer;
            transition: background 0.2s;
        }
        .examples span:hover {
            background: #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛍️ DealFinder</h1>
            <p>Find the best deals on products you love</p>
        </div>
        
        <div class="search-box">
            <form method="post" action="/swarm" class="search-form" id="searchForm">
                <input type="text" name="msg" class="search-input" 
                       placeholder="Search for deals... (e.g., 'iPhone 15 deals', 'gaming laptop under $1000')"
                       required/>
                <button type="submit" class="search-button">🔍 Find Deals</button>
            </form>
            
            <div class="examples">
                <strong>Try:</strong>
                <span onclick="setQuery('laptop deals')">laptop deals</span>
                <span onclick="setQuery('iPhone 15 price')">iPhone 15 price</span>
                <span onclick="setQuery('gaming console under $400')">gaming console under $400</span>
                <span onclick="setQuery('MacBook Air M2 discount')">MacBook Air M2 discount</span>
            </div>
        </div>
        
        <div class="results-container">
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Finding the best deals for you...</p>
            </div>
            <div id="results">{{response}}</div>
        </div>
    </div>
    
    <script>
        function setQuery(query) {
            document.querySelector('.search-input').value = query;
        }
        
        document.getElementById('searchForm').addEventListener('submit', function() {
            document.getElementById('loading').classList.add('active');
            // Don't hide results - let the new page load show them
        });
        
        // Ensure results are visible when page loads
        window.addEventListener('load', function() {
            document.getElementById('loading').classList.remove('active');
            var resultsDiv = document.getElementById('results');
            if (resultsDiv) {
                resultsDiv.style.display = 'block';
                // Debug: log what's in the results div
                console.log('Results div content length:', resultsDiv.innerHTML.length);
                console.log('Results div has price elements:', resultsDiv.querySelectorAll('.product-price').length);
            }
        });
    </script>
</body>
</html>
"""


def render_page(content: str = "") -> str:
    """Render the main HTML page with optional content."""
    return HTML_PAGE.replace("{{response}}", content)

