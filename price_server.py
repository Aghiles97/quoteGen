from flask import Flask, request, jsonify, render_template
import json
import csv
import os
from datetime import datetime
import io

app = Flask(__name__, template_folder='.')

# Configuration
PRODUCTS_FILE = 'server_products.csv'
PRICES_FILE = 'server_prices.json'
DATA_DIR = 'server_data'

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def get_file_path(filename):
    return os.path.join(DATA_DIR, filename)

# Products endpoints
@app.route('/products', methods=['GET', 'POST'])
def handle_products():
    file_path = get_file_path(PRODUCTS_FILE)
    
    if request.method == 'POST':
        try:
            csv_content = request.get_data(as_text=True).strip()
            
            # Ensure content is properly decoded
            try:
                csv_content = csv_content.encode('latin-1').decode('utf-8')
            except:
                pass  # Keep original if conversion fails
            
            print("Raw received content:", repr(csv_content))
            
            if not csv_content:
                return jsonify({'message': 'Empty CSV content received'}), 400
            
            try:
                # Parse CSV with proper quoting
                f = io.StringIO(csv_content)
                reader = csv.reader(f, quoting=csv.QUOTE_ALL, escapechar='\\')
                rows = list(reader)
                
                if not rows:
                    return jsonify({'message': 'No data in CSV content'}), 400
                
                header = [col.strip() for col in rows[0]]
                print("Processed header:", header)
                
                # Validate header and content
                expected_header = ['ID', 'Name', 'Description', 'Photo']
                if not all(col in header for col in expected_header):
                    return jsonify({
                        'message': 'Invalid CSV format',
                        'details': f'Missing columns: {[col for col in expected_header if col not in header]}',
                        'received_header': header
                    }), 400

                # Save with UTF-8 encoding
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, quoting=csv.QUOTE_ALL, escapechar='\\')
                    writer.writerows(rows)
                
                return jsonify({
                    'message': 'Products updated successfully',
                    'rows_processed': len(rows) - 1
                }), 200
                
            except csv.Error as e:
                return jsonify({
                    'message': 'CSV parsing error',
                    'details': str(e),
                    'content_preview': csv_content[:200]
                }), 400
                
        except Exception as e:
            return jsonify({
                'message': 'Server error',
                'details': str(e),
                'type': type(e).__name__
            }), 500
    
    else:  # GET request
        try:
            if not os.path.exists(file_path):
                return jsonify({'message': 'No products found'}), 404
            
            # Read with UTF-8 encoding
            products = []
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f, quoting=csv.QUOTE_ALL, escapechar='\\')
                products = list(reader)
            
            output = io.StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_ALL, escapechar='\\')
            writer.writerows(products)
            
            # Set UTF-8 content type
            return output.getvalue(), 200, {
                'Content-Type': 'text/csv; charset=utf-8'
            }
            
        except Exception as e:
            return jsonify({'message': f'Server error: {str(e)}'}), 500

# Prices endpoints
@app.route('/prices', methods=['GET', 'POST'])
def handle_prices():
    file_path = get_file_path(PRICES_FILE)
    
    if request.method == 'POST':
        try:
            # Get JSON data from request
            price_data = request.get_json()
            if not price_data:
                return jsonify({'message': 'No price data provided'}), 400
            
            # Load existing prices
            existing_prices = {}
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    existing_prices = json.load(f)
            
            # Update prices with new data
            for product_id, data in price_data.items():
                if product_id not in existing_prices:
                    existing_prices[product_id] = {
                        'name': data.get('name', ''),
                        'price': data.get('price', 0),
                        'history': []
                    }
                
                current_price = existing_prices[product_id].get('price', 0)
                if current_price != data.get('price', 0):
                    # Add to history only if price changed
                    history_entry = {
                        'price': data.get('price', 0),
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                    }
                    existing_prices[product_id]['history'].append(history_entry)
                    existing_prices[product_id]['price'] = data.get('price', 0)
                    existing_prices[product_id]['name'] = data.get('name', '')
            
            # Save updated prices
            with open(file_path, 'w') as f:
                json.dump(existing_prices, f, indent=2)
            
            return jsonify({'message': 'Prices updated successfully'}), 200
            
        except Exception as e:
            return jsonify({'message': f'Server error: {str(e)}'}), 500
    
    else:  # GET request
        try:
            if not os.path.exists(file_path):
                # Initialize empty prices file if it doesn't exist
                with open(file_path, 'w') as f:
                    json.dump({}, f)
                return jsonify({}), 200
                
            with open(file_path, 'r') as f:
                prices = json.load(f)
                print("Sending prices from server:", json.dumps(prices, indent=2))  # Debug print
            
            # Return the entire prices dictionary including history
            return jsonify(prices), 200
            
        except Exception as e:
            print(f"Error in GET /prices: {str(e)}")  # Debug print
            return jsonify({'message': f'Server error: {str(e)}'}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200


@app.route('/debug', methods=['GET'])
def debug_view():
    products = []
    prices = {}
    
    # Load products
    products_path = get_file_path(PRODUCTS_FILE)
    if os.path.exists(products_path):
        with open(products_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f, quoting=csv.QUOTE_ALL, escapechar='\\')
            products = list(reader)[1:]  # Skip header
    
    # Load prices
    prices_path = get_file_path(PRICES_FILE)
    if os.path.exists(prices_path):
        with open(prices_path, 'r') as f:
            prices = json.load(f)
    
    return render_template('index.html', products=products, prices=prices)


if __name__ == '__main__':
    # Run the server on port 5001 to avoid conflicts with common development ports
    app.run(host='0.0.0.0', port=5001, debug=True)
