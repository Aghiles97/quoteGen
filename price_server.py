from flask import Flask, request, jsonify, render_template, send_file
import json
import csv
import os
from datetime import datetime
import io
import pandas as pd
import shutil
from io import BytesIO
import zipfile

app = Flask(__name__, template_folder='.')


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'server_data')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.csv')
PRICES_FILE = os.path.join(DATA_DIR, 'product_prices.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'quotation_history.json')
STATUS_FILE = os.path.join(DATA_DIR, 'quotation_status.json')
ANALYTICS_FILE = os.path.join(DATA_DIR, 'analytics.json')
DELETIONS_FILE = os.path.join(DATA_DIR, 'deleted_quotes.json')
CATEGORIES_FILE = os.path.join(DATA_DIR, 'categories.json')

DATA_DIR = 'server_data'


# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def get_file_path(filename):
    return os.path.join(DATA_DIR, filename)

# Add new file type handling function
def handle_json_file(file_name, data=None):
    file_path = get_file_path(file_name)
    if data:  # POST request
        # Add validation for empty data structures
        if isinstance(data, dict) and not data:
            raise ValueError(f"Empty dictionary received for {file_name}")
        if isinstance(data, list) and not data:
            raise ValueError(f"Empty list received for {file_name}")
            
        # Validate specific file types
        if file_name == ANALYTICS_FILE and (not isinstance(data, list) or not data):
            raise ValueError("Analytics data must be a non-empty list")
            
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    else:  # GET request
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump({}, f)
            return {}
        with open(file_path, 'r') as f:
            return json.load(f)



@app.route('/download_all', methods=['GET'])
def download_all_files():
    """Download all server data files as a zip archive"""
    try:
        # Create an in-memory zip file
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # List of files to include in the download
            files_to_download = {
                'products.csv': PRODUCTS_FILE,
                'product_prices.json': PRICES_FILE,
                'quotation_status.json': STATUS_FILE,
                'quotation_history.json': HISTORY_FILE,
                'analytics.json': ANALYTICS_FILE,
                'categories.json': CATEGORIES_FILE,
                'deleted_quotes.json': DELETIONS_FILE
            }
            
            # Add each file to the zip if it exists
            for filename, filepath in files_to_download.items():
                if os.path.exists(filepath):
                    # Read file content
                    with open(filepath, 'rb') as f:
                        file_content = f.read()
                    # Write to zip with proper filename
                    zf.writestr(filename, file_content)
                else:
                    # Create empty file if it doesn't exist
                    if filename.endswith('.json'):
                        zf.writestr(filename, '{}')
                    elif filename.endswith('.csv'):
                        zf.writestr(filename, 'ID,Name,Description,Photo,Category\n')
        
        # Reset file pointer to beginning
        memory_file.seek(0)
        
        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"quotation_data_{timestamp}.zip"
        
        # Send the file
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=download_filename
        )
        
    except Exception as e:
        error_message = f"Download failed: {str(e)}"
        print(error_message)  # Server-side logging
        return jsonify({
            'status': 'error',
            'message': error_message
        }), 500
    

# Add this new route for categories
@app.route('/categories', methods=['GET', 'POST'])
def handle_categories():
    """Handle categories data"""
    try:
        if request.method == 'POST':
            categories_data = request.get_json()
            if not categories_data:
                return jsonify({'message': 'No categories data provided'}), 400
                
            # Save categories data
            with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(categories_data, f, indent=2)
            
            return jsonify({'message': 'Categories updated successfully'}), 200
            
        else:  # GET request
            if not os.path.exists(CATEGORIES_FILE):
                # Initialize with default categories if file doesn't exist
                default_categories = [
                    {"id": "equipment", "name": "Equipment"},
                    {"id": "tools", "name": "Tools"},
                    {"id": "consumables", "name": "Consumables"},
                    {"id": "other", "name": "Uncategorized"}
                ]
                with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_categories, f, indent=2)
                return jsonify(default_categories), 200
                
            # Return categories data
            with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                categories = json.load(f)
            return jsonify(categories), 200
            
    except Exception as e:
        print(f"Error handling categories: {str(e)}")  # Debug print
        return jsonify({'message': f'Server error: {str(e)}'}), 500

# Add this specific category endpoint for single category operations
@app.route('/categories/<category_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_category(category_id):
    """Handle operations on a single category"""
    try:
        # Load current categories
        if not os.path.exists(CATEGORIES_FILE):
            # Initialize with default categories if file doesn't exist
            default_categories = [
                {"id": "equipment", "name": "Equipment"},
                {"id": "tools", "name": "Tools"},
                {"id": "consumables", "name": "Consumables"},
                {"id": "other", "name": "Uncategorized"}
            ]
            categories = default_categories
        else:
            with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                categories = json.load(f)
        
        if request.method == 'GET':
            # Find and return the specific category
            category = next((cat for cat in categories if cat['id'] == category_id), None)
            if category:
                return jsonify(category), 200
            else:
                return jsonify({'message': 'Category not found'}), 404
        
        elif request.method == 'PUT':
            # Update a category
            category_data = request.get_json()
            if not category_data or 'name' not in category_data:
                return jsonify({'message': 'Invalid category data'}), 400
                
            # Find and update category
            category_found = False
            for i, cat in enumerate(categories):
                if cat['id'] == category_id:
                    categories[i]['name'] = category_data['name']
                    category_found = True
                    break
            
            if not category_found:
                # Add new category if not found
                categories.append({
                    'id': category_id,
                    'name': category_data['name']
                })
                
            # Save updated categories
            with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(categories, f, indent=2)
                
            return jsonify({'message': 'Category updated successfully'}), 200
        
        elif request.method == 'DELETE':
            # Remove category with given ID
            original_len = len(categories)
            categories = [cat for cat in categories if cat['id'] != category_id]
            
            if len(categories) == original_len:
                return jsonify({'message': 'Category not found'}), 404
                
            # Save updated categories
            with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(categories, f, indent=2)
                
            return jsonify({'message': 'Category deleted successfully'}), 200
            
    except Exception as e:
        print(f"Error handling single category: {str(e)}")
        return jsonify({'message': f'Server error: {str(e)}'}), 500


# Products endpoints
@app.route('/products', methods=['GET', 'POST'])
def handle_products():
    file_path = get_file_path(PRODUCTS_FILE)
    
    if request.method == 'POST':
        try:
            if 'file' in request.files:
                file = request.files['file']
                print('File: File; FIle FILE FILE FLE : ', request.files)
                file.save('server_data/products.csv')
                return 'OK', 200

                
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
        
@app.route('/products/<product_id>', methods=['POST'])
def update_single_product(product_id):
    """Update or create a single product by ID"""
    try:
        # Get the product data from request
        product_data = request.get_json()
        print(product_data)
        if not product_data:
            return jsonify({'message': 'No product data provided'}), 400

        # Load existing products
        products = []
        header = ['ID', 'Name', 'Description', 'Photo', 'Category']  # Updated to include Category
        if os.path.exists(PRODUCTS_FILE):
            df = pd.read_csv(PRODUCTS_FILE, quoting=csv.QUOTE_ALL, escapechar='\\', encoding='utf-8')
            products = df.values.tolist()
        else:
            # Create new file with header if it doesn't exist
            df = pd.DataFrame(columns=header)
            df.to_csv(PRODUCTS_FILE, index=False, quoting=csv.QUOTE_ALL, escapechar='\\', encoding='utf-8')

        # Check if product exists
        product_exists = False
        for i, product in enumerate(products):
            if product[0] == product_id:
                # Update existing product
                products[i] = [
                    product_id,
                    product_data['name'],
                    product_data['description'],
                    product_data['photo'],
                    product_data.get('category', 'other')  # Add category field with default 'other'
                ]
                product_exists = True
                break

        if not product_exists:
            # Add new product
            products.append([
                product_id,
                product_data['name'],
                product_data['description'],
                product_data['photo'],
                product_data.get('category', 'other')  # Add category field with default 'other'
            ])
        print("product_data['photo']: ", product_data['photo'])

        # Save updated products back to CSV
        df = pd.DataFrame(products, columns=header)  # Use updated header
        df.to_csv(PRODUCTS_FILE, index=False, quoting=csv.QUOTE_ALL, escapechar='\\', encoding='utf-8')

        return jsonify({
            'message': 'Product updated successfully' if product_exists else 'Product created successfully',
            'product': {
                'id': product_id,
                'name': product_data['name'],
                'description': product_data['description'],
                'photo': product_data['photo'],
                'category': product_data.get('category', 'other')  # Add category to response
            }
        }), 200

    except Exception as e:
        return jsonify({'message': f'Error updating/creating product: {str(e)}'}), 500
    
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
                        'history': data.get('history', []),  # Preserve incoming history
                        'last_modified': data.get('last_modified', datetime.now().strftime('%Y-%m-%d %H:%M'))
                    }
                else:
                    current_price = existing_prices[product_id].get('price', 0)
                    if current_price != data.get('price', 0):
                        # Add to history only if price changed
                        history_entry = {
                            'price': data.get('price', 0),
                            'date': datetime.now().strftime('%Y-%m-%d %H:%M')
                        }
                        # Merge existing history with incoming history
                        existing_history = existing_prices[product_id].get('history', [])
                        incoming_history = data.get('history', [])
                        merged_history = list({(entry.get('date'), entry.get('price')): entry 
                                            for entry in existing_history + incoming_history}.values())
                        merged_history.append(history_entry)
                        
                        existing_prices[product_id].update({
                            'price': data.get('price', 0),
                            'name': data.get('name', ''),
                            'history': merged_history,
                            'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M')
                        })
                    else:
                        # Only update name and preserve existing history if price hasn't changed
                        existing_prices[product_id]['name'] = data.get('name', '')
                        existing_prices[product_id]['history'] = (
                            data.get('history', existing_prices[product_id].get('history', []))
                        )
                        if 'last_modified' in data:
                            existing_prices[product_id]['last_modified'] = data['last_modified']
            
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
            
            # Return the entire prices dictionary including history
            return jsonify(prices), 200
            
        except Exception as e:
            print(f"Error in GET /prices: {str(e)}")  # Debug print
            return jsonify({'message': f'Server error: {str(e)}'}), 500


@app.route('/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    products_path = get_file_path(PRODUCTS_FILE)
    try:
        # Read existing products
        products = []
        with open(products_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f, quoting=csv.QUOTE_ALL, escapechar='\\')
            products = list(reader)
            
        # Find and remove the product
        header = products[0]
        filtered_products = [row for row in products[1:] if row[0] != product_id]
        
        # Write back the filtered products
        with open(products_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL, escapechar='\\')
            writer.writerow(header)
            writer.writerows(filtered_products)
            
        return jsonify({'message': 'Product deleted successfully'}), 200
    except Exception as e:
        return jsonify({'message': f'Error deleting product: {str(e)}'}), 500


@app.route('/prices/<product_id>', methods=['POST'])
def update_single_price(product_id):
    try:
        # Load current prices
        prices_path = get_file_path(PRICES_FILE)
        with open(prices_path, 'r') as f:
            prices = json.load(f)
        
        # Update single product price
        prices[product_id] = request.json
        
        # Save updated prices
        with open(prices_path, 'w') as f:
            json.dump(prices, f, indent=2)
            
        return jsonify({'message': 'Price updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/prices/<product_id>', methods=['DELETE'])
def delete_price(product_id):
    prices_path = get_file_path(PRICES_FILE)
    try:
        # Read existing prices
        with open(prices_path, 'r') as f:
            prices = json.load(f)
            
        # Remove price if exists
        if product_id in prices:
            del prices[product_id]
            
            # Write back updated prices
            with open(prices_path, 'w') as f:
                json.dump(prices, f, indent=2)
                
            return jsonify({'message': 'Price deleted successfully'}), 200
        else:
            return jsonify({'message': 'Price not found'}), 404
    except Exception as e:
        return jsonify({'message': f'Error deleting price: {str(e)}'}), 500
    

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200
@app.route('/history', methods=['GET', 'POST'])
def handle_history():
    try:
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'message': 'No history data provided'}), 400
            handle_json_file(HISTORY_FILE, data)
            return jsonify({'message': 'History updated successfully'}), 200
        else:
            history = handle_json_file(HISTORY_FILE)
            return jsonify(history), 200
    except Exception as e:
        return jsonify({'message': f'Server error: {str(e)}'}), 500

@app.route('/status', methods=['GET', 'POST'])
def handle_status():
    try:
        if request.method == 'POST':
            data = request.get_json()
            print(data)
            if not data:
                return jsonify({'message': 'No status data provided'}), 400
            handle_json_file(STATUS_FILE, data)
            return jsonify({'message': 'Status updated successfully'}), 200
        else:
            status = handle_json_file(STATUS_FILE)
            return jsonify(status), 200
    except Exception as e:
        return jsonify({'message': f'Server error: {str(e)}'}), 500

@app.route('/analytics', methods=['GET', 'POST'])
def handle_analytics():
    try:
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'message': 'No analytics data provided'}), 400
            try:
                handle_json_file(ANALYTICS_FILE, data)
                return jsonify({'message': 'Analytics updated successfully'}), 200
            except ValueError as e:
                return jsonify({'message': str(e)}), 400
        else:
            analytics = handle_json_file(ANALYTICS_FILE)
            return jsonify(analytics), 200
    except Exception as e:
        return jsonify({'message': f'Server error: {str(e)}'}), 500


# Add this after your other route definitions

@app.route('/quotes', methods=['GET', 'POST'])
def handle_quotes():
    """Handle quotes data"""
    try:
        if request.method == 'POST':
            new_quotes = request.get_json()
            if not new_quotes:
                return jsonify({'message': 'No quotes data provided'}), 400
                
            # Load existing quotes
            existing_quotes = {}
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    existing_quotes = json.load(f)
            
            # Merge new quotes with existing ones
            existing_quotes.update(new_quotes)
                
            # Save merged quotes
            with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(existing_quotes, f, indent=2)
            
            return jsonify({'message': 'Quotes updated successfully'}), 200
            
        else:  # GET request
            if not os.path.exists(STATUS_FILE):
                # Initialize empty quotes file if it doesn't exist
                with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                return jsonify({}), 200
                
            # Return quotes data from quotation_status.json
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                quotes = json.load(f)
            return jsonify(quotes), 200
            
    except Exception as e:
        print(f"Error in handle_quotes: {str(e)}")  # Debug print
        return jsonify({'message': f'Server error: {str(e)}'}), 500
    
@app.route('/quotes/<quote_id>', methods=['DELETE'])
def delete_quote(quote_id):
    """Delete a specific quote from status, history and analytics"""
    try:
        # Load data from all files
        status_data = {}
        history_data = []
        analytics_data = []
        
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
                
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                
        if os.path.exists(ANALYTICS_FILE):
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                analytics_data = json.load(f)
        
        # Check if quote exists
        if quote_id not in status_data:
            return jsonify({'message': 'Quote not found'}), 404
            
        # Get the quote date for filtering history and analytics
        quote_date = status_data[quote_id]['date']
        
        # Delete from status
        del status_data[quote_id]
        
        # Filter out from history
        history_data = [h for h in history_data if h['date'] != quote_date]
        
        # Filter out from analytics
        analytics_data = [a for a in analytics_data if a['date'] != quote_date]
        
        # Save all updated data
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2)
            
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2)
            
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(analytics_data, f, indent=2)
            
        return jsonify({
            'message': 'Quote deleted successfully from all records',
            'quote_id': quote_id
        }), 200
        
    except Exception as e:
        print(f"Error deleting quote: {str(e)}")  # Debug print
        return jsonify({
            'message': f'Server error while deleting quote: {str(e)}',
            'quote_id': quote_id
        }), 500
    


# Update debug view to show categories
@app.route('/debug', methods=['GET'])
def debug_view():
    data = {
        'products': [],
        'prices': {},
        'history': {},
        'status': {},
        'analytics': {},
        'categories': []  # Add categories to debug view
    }
    
    # Load products
    products_path = get_file_path(PRODUCTS_FILE)
    if os.path.exists(products_path):
        with open(products_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f, quoting=csv.QUOTE_ALL, escapechar='\\')
            data['products'] = list(reader)[1:]  # Skip header
    
    # Load categories
    if os.path.exists(CATEGORIES_FILE):
        with open(CATEGORIES_FILE, 'r') as f:
            data['categories'] = json.load(f)
    
    # Load other JSON files
    for file_type in ['prices', 'history', 'status', 'analytics']:
        file_path = get_file_path(f'server_{file_type}.json')
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data[file_type] = json.load(f)
    
    return render_template('index.html', **data)


# Update the backup function to include categories file
@app.route('/backup', methods=['POST'])
def create_server_backup():
    """Create a backup of all server data files"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(DATA_DIR, 'server_backups', f'backup_{timestamp}')
        os.makedirs(backup_dir, exist_ok=True)
        
        # List of files to backup with their proper paths
        files_to_backup = {
            'products.csv': PRODUCTS_FILE,
            'product_prices.json': PRICES_FILE,
            'quotation_status.json': STATUS_FILE,
            'quotation_history.json': HISTORY_FILE,
            'analytics.json': ANALYTICS_FILE,
            'categories.json': CATEGORIES_FILE  # Add categories file to backup
        }
        
        backed_up_files = []
        for filename, filepath in files_to_backup.items():
            if os.path.exists(filepath):
                backup_path = os.path.join(backup_dir, filename)
                shutil.copy2(filepath, backup_path)
                backed_up_files.append(filename)
        
        if not backed_up_files:
            raise Exception("No files were backed up - no data files found")
            
        update_message = f"Backed up {len(backed_up_files)} files: {', '.join(backed_up_files)}"
        
        return jsonify({
            'status': 'success',
            'backup_path': backup_dir,
            'message': update_message,
            'files_backed_up': backed_up_files,
            'timestamp': timestamp
        }), 200
        
    except Exception as e:
        error_message = f"Backup failed: {str(e)}"
        print(error_message)  # Server-side logging
        return jsonify({
            'status': 'error',
            'message': error_message
        }), 500


if __name__ == '__main__':
    # Run the server on port 5001 to avoid conflicts with common development ports
    app.run(host='0.0.0.0', port=5001, debug=True)
