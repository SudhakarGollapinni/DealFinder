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
        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        .modal-content {
            background-color: white;
            margin: 15% auto;
            padding: 30px;
            border-radius: 12px;
            width: 90%;
            max-width: 500px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-header h2 {
            margin: 0;
            color: #2d3748;
        }
        .close {
            color: #aaa;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }
        .close:hover {
            color: #000;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #4a5568;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 6px;
            font-size: 14px;
            box-sizing: border-box;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        .form-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
        }
        .btn-primary {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-primary:hover {
            background: #5568d3;
        }
        .btn-secondary {
            background: #e2e8f0;
            color: #4a5568;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
        }
        .btn-secondary:hover {
            background: #cbd5e0;
        }
        .error-message {
            color: #e53e3e;
            font-size: 14px;
            margin-top: 8px;
        }
        .success-message {
            color: #48bb78;
            font-size: 14px;
            margin-top: 8px;
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
        // Define openNotifyModal FIRST, before anything else that might need it
        window.openNotifyModal = function(searchQuery) {
            console.log('=== openNotifyModal called ===');
            console.log('Search query:', searchQuery);
            
            const modal = document.getElementById('notifyModal');
            if (!modal) {
                console.error('❌ Modal element not found!');
                alert('Modal not found. Please refresh the page.');
                return false;
            }
            console.log('✅ Modal element found');
            
            modal.style.display = 'block';
            console.log('✅ Modal display set to block');
            
            const productNameInput = document.getElementById('notifyProductName');
            if (productNameInput) {
                productNameInput.value = searchQuery;
                console.log('✅ Set product name to:', searchQuery);
            } else {
                console.error('❌ Product name input not found!');
            }
            
            // Update modal title to reflect search query
            const modalTitle = document.querySelector('#notifyModal h2');
            if (modalTitle) {
                modalTitle.textContent = '🔔 Get Price Drop Alerts for "' + searchQuery + '"';
                console.log('✅ Updated modal title');
            }
            
            const emailInput = document.getElementById('notifyEmail');
            const phoneInput = document.getElementById('notifyPhone');
            const messageDiv = document.getElementById('notifyMessage');
            
            if (emailInput) emailInput.value = '';
            if (phoneInput) phoneInput.value = '';
            if (messageDiv) messageDiv.innerHTML = '';
            
            console.log('✅ Modal should now be visible');
            return false;
        };
        
        // Also define as regular function for compatibility
        function openNotifyModal(searchQuery) {
            return window.openNotifyModal(searchQuery);
        }
        
        console.log('✅ openNotifyModal function defined on window');
        
        function setQuery(query) {
            document.querySelector('.search-input').value = query;
        }
        
        // Handler for notify button click - reads query from data attribute
        function handleNotifyClick(button) {
            console.log('=== handleNotifyClick called ===');
            console.log('Button:', button);
            const queryAttr = button.getAttribute('data-query');
            console.log('Query attribute:', queryAttr);
            if (!queryAttr) {
                console.error('No data-query attribute found');
                return false;
            }
            
            // Check if function is available
            console.log('window.openNotifyModal type:', typeof window.openNotifyModal);
            console.log('openNotifyModal type:', typeof openNotifyModal);
            
            if (typeof window.openNotifyModal !== 'function') {
                console.error('openNotifyModal function not found!');
                console.log('Available on window:', Object.keys(window).filter(k => k.includes('Notify')));
                alert('Notification feature is loading. Please refresh the page and try again.');
                return false;
            }
            
            try {
                // Parse the JSON string from the data attribute
                const query = JSON.parse(queryAttr);
                console.log('Parsed query:', query);
                console.log('Calling window.openNotifyModal...');
                window.openNotifyModal(query);
            } catch (e) {
                console.error('Error parsing query:', e);
                // Fallback: use the raw value
                console.log('Using raw query value');
                window.openNotifyModal(queryAttr);
            }
            return false;
        }
        
        // Make handleNotifyClick globally available
        window.handleNotifyClick = handleNotifyClick;
        
        // Verify function is available on page load
        console.log('✅ handleNotifyClick defined, window.openNotifyModal:', typeof window.openNotifyModal);
        
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
            
            // Verify notify button exists and function is available
            setTimeout(function() {
                const notifyBtn = document.querySelector('.notify-button');
                console.log('Notify button found:', !!notifyBtn);
                if (notifyBtn) {
                    console.log('Notify button data-query:', notifyBtn.getAttribute('data-query'));
                }
                console.log('handleNotifyClick function available:', typeof window.handleNotifyClick);
                console.log('openNotifyModal function available:', typeof window.openNotifyModal);
            }, 100);
        });
        
        // Also set up on DOMContentLoaded for faster initialization
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded, handleNotifyClick available:', typeof window.handleNotifyClick);
            console.log('openNotifyModal available:', typeof window.openNotifyModal);
            console.log('Modal element exists:', !!document.getElementById('notifyModal'));
        });
    </script>
    
    <!-- Notification Modal -->
    <div id="notifyModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>🔔 Get Price Drop Alerts</h2>
                <span class="close" onclick="closeNotifyModal()">&times;</span>
            </div>
            <form id="notifyForm" onsubmit="submitNotification(event)">
                <input type="hidden" id="notifyProductName" name="product_name">
                <p style="color: #4a5568; margin-bottom: 20px;">We'll notify you when prices drop for products matching your search query.</p>
                <div class="form-group">
                    <label for="notifyEmail">Email Address (optional)</label>
                    <input type="email" id="notifyEmail" name="email" placeholder="your@email.com">
                </div>
                <div class="form-group">
                    <label for="notifyPhone">Phone Number (optional)</label>
                    <input type="tel" id="notifyPhone" name="phone" placeholder="+1234567890">
                </div>
                <div id="notifyMessage"></div>
                <div class="form-actions">
                    <button type="button" class="btn-secondary" onclick="closeNotifyModal()">Cancel</button>
                    <button type="submit" class="btn-primary">Subscribe</button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        // openNotifyModal is already defined in the first script tag above
        // This script tag is for the modal-related functions
        
        function closeNotifyModal() {
            document.getElementById('notifyModal').style.display = 'none';
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('notifyModal');
            if (event.target == modal) {
                closeNotifyModal();
            }
        }
        
        async function submitNotification(event) {
            event.preventDefault();
            
            const productName = document.getElementById('notifyProductName').value;
            const email = document.getElementById('notifyEmail').value.trim();
            const phone = document.getElementById('notifyPhone').value.trim();
            const messageDiv = document.getElementById('notifyMessage');
            
            // Validate that at least one contact method is provided
            if (!email && !phone) {
                messageDiv.innerHTML = '<div class="error-message">Please provide at least an email or phone number.</div>';
                return;
            }
            
            // Basic email validation
            if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
                messageDiv.innerHTML = '<div class="error-message">Please enter a valid email address.</div>';
                return;
            }
            
            // Basic phone validation (at least 10 digits)
            if (phone && !/^[\d\s\-\+\(\)]{10,}$/.test(phone)) {
                messageDiv.innerHTML = '<div class="error-message">Please enter a valid phone number.</div>';
                return;
            }
            
            try {
                const response = await fetch('/api/notify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        product_name: productName,
                        email: email || null,
                        phone: phone || null
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    messageDiv.innerHTML = '<div class="success-message">✅ You\'ll be notified when prices drop for this product!</div>';
                    // Close modal after 2 seconds
                    setTimeout(() => {
                        closeNotifyModal();
                    }, 2000);
                } else {
                    messageDiv.innerHTML = `<div class="error-message">${data.detail || 'An error occurred. Please try again.'}</div>`;
                }
            } catch (error) {
                messageDiv.innerHTML = '<div class="error-message">Network error. Please try again.</div>';
                console.error('Error:', error);
            }
        }
    </script>
</body>
</html>
"""


def render_page(content: str = "") -> str:
    """Render the main HTML page with optional content."""
    return HTML_PAGE.replace("{{response}}", content)

