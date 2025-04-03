import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from pymongo import MongoClient
import matplotlib.pyplot as plt
import io

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # Hiển thị từ INFO trở lên
)
logger = logging.getLogger(__name__)

# Tắt logging của các thư viện khác
logging.getLogger('httpx').setLevel(logging.ERROR)
logging.getLogger('telegram').setLevel(logging.ERROR)

# Emoji cho từng danh mục
CATEGORY_EMOJIS = {
    'Ăn uống': '🍴',
    'Di chuyển': '🚗',
    'Mua sắm': '🛍️',
    'Giải trí': '🎮',
    'Sức khỏe': '💪',
    'Học tập': '📚',
    'Làm đẹp': '💅',
    'Hóa đơn & Tiện ích': '📝',
    'Khác': '📌'
}

# Danh sách các danh mục
CATEGORIES = list(CATEGORY_EMOJIS.keys())

# MongoDB connection
try:
    client = MongoClient(os.getenv('MONGODB_URI'))
    # Test the connection
    client.admin.command('ping')
    print("✅ Kết nối MongoDB thành công!")
    db = client[os.getenv('DATABASE_NAME')]
except Exception as e:
    print(f"❌ Lỗi kết nối MongoDB: {e}")
    raise

# Collections
thuchi_collections = {}  # Dictionary to store user-specific collections

def get_user_collection(user_id):
    """Get or create a collection for a specific user."""
    try:
        collection_name = f'thuchi_{user_id}'
        if collection_name not in thuchi_collections:
            thuchi_collections[collection_name] = db[collection_name]
        return thuchi_collections[collection_name]
    except Exception as e:
        print(f"❌ Lỗi khi tạo collection cho user {user_id}: {e}")
        raise

# Keywords collection
tu_khoa_collection = db['tu_khoa']

def get_expense_category(description: str) -> str:
    """Xác định danh mục chi tiêu dựa trên mô tả."""
    description = description.lower()
    
    # Tìm từ khóa khớp với description
    keyword_doc = tu_khoa_collection.find_one({'tu_khoa': description})
    if keyword_doc:
        return keyword_doc['danh_muc']
        
    # Nếu không tìm thấy khớp chính xác, tìm từ khóa là substring
    all_keywords = list(tu_khoa_collection.find().sort('tu_khoa', -1))  # Sắp xếp giảm dần để ưu tiên từ dài hơn
    for keyword_doc in all_keywords:
        if keyword_doc['tu_khoa'] in description:
            return keyword_doc['danh_muc']
    
    return 'Khác'

def is_admin(user_id: int) -> bool:
    """Kiểm tra xem user có phải là admin không."""
    admin_id = int(os.getenv('ADMIN_ID', 0))
    return user_id == admin_id

async def show_menu(update: Update):
    """Hiển thị menu chính."""
    user_id = update.effective_user.id
    keyboard = [
        [
            InlineKeyboardButton("Nhập số tiền ban đầu", callback_data='nhap_tien'),
            InlineKeyboardButton("Thêm tiền", callback_data='them_tien')
        ],
        [
            InlineKeyboardButton("Xem số tiền còn lại", callback_data='xem_tien'),
            InlineKeyboardButton("Phân tích chi tiêu", callback_data='phan_tich')
        ],
        [
            InlineKeyboardButton("Tổng hợp chi tiêu", callback_data='tong_hop'),
            InlineKeyboardButton("Xem chi tiêu theo tháng", callback_data='xem_thang')
        ],
        [
            InlineKeyboardButton("☕️ Buy me a coffee", callback_data='donate')
        ]
    ]
    
    # Chỉ hiển thị nút Quản lý từ khóa cho admin
    if is_admin(user_id):
        keyboard.append([
            InlineKeyboardButton("Quản lý từ khóa", callback_data='quan_ly_tu_khoa'),
            InlineKeyboardButton("❌ Xóa dữ liệu", callback_data='xoa_du_lieu')
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("❌ Xóa dữ liệu", callback_data='xoa_du_lieu')
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Xử lý cả hai trường hợp: tin nhắn thông thường và callback query
    if update.message:
        await update.message.reply_text('📋 Menu chức năng:', reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text('📋 Menu chức năng:', reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    keyboard = [
        [
            InlineKeyboardButton("Nhập số tiền ban đầu", callback_data='nhap_tien'),
            InlineKeyboardButton("Thêm tiền", callback_data='them_tien')
        ],
        [
            InlineKeyboardButton("Xem số tiền còn lại", callback_data='xem_tien'),
            InlineKeyboardButton("Phân tích chi tiêu", callback_data='phan_tich')
        ],
        [
            InlineKeyboardButton("Tổng hợp chi tiêu", callback_data='tong_hop'),
            InlineKeyboardButton("Xem chi tiêu theo tháng", callback_data='xem_thang')
        ],
        [
            InlineKeyboardButton("☕️ Buy me a coffee", callback_data='donate')
        ]
    ]
    
    # Chỉ hiển thị nút Quản lý từ khóa cho admin
    if is_admin(user_id):
        keyboard.append([
            InlineKeyboardButton("Quản lý từ khóa", callback_data='quan_ly_tu_khoa'),
            InlineKeyboardButton("❌ Xóa dữ liệu", callback_data='xoa_du_lieu')
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("❌ Xóa dữ liệu", callback_data='xoa_du_lieu')
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Chào mừng bạn đến với bot quản lý thu chi! 👋\n\n'
        '💡 Cách sử dụng:\n'
        '• Nhập chi tiêu: 50k ăn sáng\n'
        '• Định dạng số tiền: 50k hoặc 1.2m\n'
        '• Ví dụ: 80k xăng, 25k trà sữa, 2.5m tiền nhà\n\n'
        'Vui lòng chọn chức năng:',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == 'donate':
        # Gửi ảnh QR code và lời cảm ơn
        message = (
            "☕️ Cảm ơn bạn đã sử dụng bot!\n\n"
            "Nếu bạn thấy bot hữu ích, hãy ủng hộ mình một ly cà phê nhé!\n"
            "Mọi đóng góp của bạn sẽ giúp mình có thêm động lực phát triển bot tốt hơn.\n\n"
            "🏦 Thông tin chuyển khoản:\n"
            "- Ngân hàng: Techcombank\n"
            "- Số tài khoản: 19073419928011\n"
            "- Chủ tài khoản: HO LONG VU\n\n"
            "🙏 Cảm ơn sự ủng hộ của bạn!"
        )
        await query.message.reply_photo(
            photo="https://img.vietqr.io/image/TCB-19073419928011-print.png?accountName=ho%20long%20vu",
            caption=message
        )
        await show_menu(update)
    elif query.data == 'nhap_tien':
        await query.message.reply_text(
            'Vui lòng nhập số tiền ban đầu theo định dạng:\n'
            'nhap_tien [số tiền]\n'
            'Ví dụ: nhap_tien 1000000'
        )
    elif query.data == 'them_tien':
        await query.message.reply_text(
            'Vui lòng nhập số tiền thêm vào theo định dạng:\n'
            'them_tien [số tiền]\n'
            'Ví dụ: them_tien 500000'
        )
    elif query.data == 'xem_tien':
        await xem_so_du(update, context)
        await show_menu(update)
    elif query.data == 'phan_tich':
        await phan_tich_chi_tieu(update, context)
        await show_menu(update)
    elif query.data == 'tong_hop':
        await tong_hop_chi_tieu(update, context)
        await show_menu(update)
    elif query.data == 'xem_thang':
        await query.message.reply_text(
            'Vui lòng nhập tháng năm cần xem theo định dạng:\n'
            'xem_thang [mm/yyyy]\n'
            'Ví dụ: xem_thang 03/2024 hoặc xem_thang 3/2024'
        )
    elif query.data == 'quan_ly_tu_khoa':
        if not is_admin(user_id):
            await query.message.reply_text('❌ Bạn không có quyền sử dụng chức năng này!')
            return
            
        # Hiển thị menu quản lý từ khóa
        keyboard = [
            [
                InlineKeyboardButton("Thêm từ khóa", callback_data='them_tu_khoa'),
                InlineKeyboardButton("Xem từ khóa", callback_data='xem_tu_khoa')
            ],
            [
                InlineKeyboardButton("Xóa từ khóa", callback_data='xoa_tu_khoa')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            'Quản lý từ khóa:\n'
            'Chọn chức năng bạn muốn thực hiện:',
            reply_markup=reply_markup
        )
    elif query.data == 'them_tu_khoa':
        if not is_admin(user_id):
            await query.message.reply_text('❌ Bạn không có quyền sử dụng chức năng này!')
            return
            
        await query.message.reply_text(
            'Vui lòng nhập từ khóa mới theo định dạng:\n'
            'tk [từ khóa] [số thứ tự]\n\n'
            'Danh sách danh mục:\n' +
            '\n'.join([f'{i+1}. {CATEGORY_EMOJIS[cat]} {cat}' for i, cat in enumerate(CATEGORIES)]) +
            '\n\nVí dụ: tk highlands 1'
        )
    elif query.data == 'xem_tu_khoa':
        if not is_admin(user_id):
            await query.message.reply_text('❌ Bạn không có quyền sử dụng chức năng này!')
            return
            
        await xem_tu_khoa(update, context)
        await show_menu(update)
    elif query.data == 'xoa_tu_khoa':
        if not is_admin(user_id):
            await query.message.reply_text('❌ Bạn không có quyền sử dụng chức năng này!')
            return
            
        await query.message.reply_text(
            'Vui lòng nhập từ khóa cần xóa theo định dạng:\n'
            'xk [từ khóa]\n'
            'Ví dụ: xk highlands'
        )
    elif query.data == 'xoa_du_lieu':
        # Hiển thị menu xóa dữ liệu
        keyboard = [
            [
                InlineKeyboardButton("❌ Xóa toàn bộ dữ liệu", callback_data='xoa_tat_ca'),
                InlineKeyboardButton("🗓 Xóa theo ngày", callback_data='xoa_theo_ngay')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            '⚠️ Xóa dữ liệu:\n'
            'Chọn chức năng bạn muốn thực hiện:',
            reply_markup=reply_markup
        )
    elif query.data == 'xoa_tat_ca':
        await query.message.reply_text(
            '⚠️ Bạn có chắc chắn muốn xóa toàn bộ dữ liệu chi tiêu của mình?\n'
            'Hành động này không thể hoàn tác!\n\n'
            'Nhập "xoa_du_lieu xac_nhan" để xác nhận xóa.'
        )
    elif query.data == 'xoa_theo_ngay':
        await query.message.reply_text(
            'Vui lòng nhập ngày cần xóa theo định dạng:\n'
            'xoa_ngay [dd/mm/yyyy]\n'
            'Ví dụ: xoa_ngay 15/03/2024'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages."""
    text = update.message.text.lower()
    user_id = update.effective_user.id
    
    if text.startswith('tk ') or text.startswith('them_tu_khoa '):  # Hỗ trợ cả 2 cách
        if not is_admin(user_id):
            await update.message.reply_text('❌ Bạn không có quyền sử dụng chức năng này!')
            return
            
        try:
            parts = text.split(' ', 2)
            tu_khoa = parts[1]
            stt_danh_muc = int(parts[2])
            
            # Kiểm tra số thứ tự danh mục hợp lệ
            if stt_danh_muc < 1 or stt_danh_muc > len(CATEGORIES):
                await update.message.reply_text(
                    'Số thứ tự danh mục không hợp lệ. Vui lòng chọn một trong các danh mục sau:\n' +
                    '\n'.join([f'{i+1}. {CATEGORY_EMOJIS[cat]} {cat}' for i, cat in enumerate(CATEGORIES)])
                )
                await show_menu(update)
                return
            
            # Lấy tên danh mục từ số thứ tự
            danh_muc = CATEGORIES[stt_danh_muc - 1]
            await them_tu_khoa(update, context, tu_khoa, danh_muc)
            await show_menu(update)
        except (IndexError, ValueError):
            await update.message.reply_text(
                'Vui lòng nhập đúng định dạng: tk [từ khóa] [số thứ tự]\n\n'
                'Danh sách danh mục:\n' +
                '\n'.join([f'{i+1}. {CATEGORY_EMOJIS[cat]} {cat}' for i, cat in enumerate(CATEGORIES)])
            )
            await show_menu(update)
    
    elif text.startswith('xk ') or text.startswith('xoa_tu_khoa '):  # Hỗ trợ cả 2 cách
        if not is_admin(user_id):
            await update.message.reply_text('❌ Bạn không có quyền sử dụng chức năng này!')
            return
            
        try:
            tu_khoa = text.split(' ', 1)[1]
            await xoa_tu_khoa(update, context, tu_khoa)
            await show_menu(update)
        except IndexError:
            await update.message.reply_text('Vui lòng nhập đúng định dạng: xk [từ khóa]')
            await show_menu(update)
    
    elif text.startswith('nhap_tien '):
        try:
            so_tien = int(text.split()[1])
            await nhap_tien_ban_dau(update, context, so_tien)
            await show_menu(update)
        except (IndexError, ValueError):
            await update.message.reply_text('Vui lòng nhập đúng định dạng: nhap_tien [số tiền]')
            await show_menu(update)
    
    elif text.startswith('them_tien '):
        try:
            so_tien = int(text.split()[1])
            await them_tien(update, context, so_tien)
            await show_menu(update)
        except (IndexError, ValueError):
            await update.message.reply_text('Vui lòng nhập đúng định dạng: them_tien [số tiền]')
            await show_menu(update)
    
    elif text.startswith('xem_thang '):
        try:
            thang_nam = text.split()[1]
            thang, nam = thang_nam.split('/')
            thang = thang.zfill(2)
            month_str = f"{nam}-{thang}"
            await xem_chi_tieu_theo_thang(update, context, month_str)
            await show_menu(update)
        except (IndexError, ValueError):
            await update.message.reply_text('Vui lòng nhập đúng định dạng: xem_thang mm/yyyy (ví dụ: xem_thang 03/2024)')
            await show_menu(update)
    
    elif text == 'xoa_du_lieu xac_nhan':
        await xoa_du_lieu(update, context)
        await show_menu(update)
    
    elif text.startswith('xoa_ngay '):
        try:
            ngay = text.split(' ', 1)[1]
            await xoa_du_lieu_theo_ngay(update, context, ngay)
            await show_menu(update)
        except IndexError:
            await update.message.reply_text('Vui lòng nhập đúng định dạng: xoa_ngay [dd/mm/yyyy]')
            await show_menu(update)
    
    else:
        # Handle expense input
        try:
            # Split message into amount and description
            parts = text.split(' ', 1)
            if len(parts) != 2:
                return
            
            amount_str = parts[0].lower()
            description = parts[1].lower()
            
            # Convert amount to number
            amount = 0
            if amount_str.endswith('k'):
                amount = int(amount_str[:-1]) * 1000
            elif amount_str.endswith('tr'):
                amount = int(amount_str[:-2]) * 1000000
            else:
                amount = int(amount_str)
            
            # Get user's collection
            thuchi_collection = get_user_collection(update.effective_user.id)
            
            # Get current month
            current_month = datetime.now().strftime('%Y-%m')
            
            # Check if user has initialized balance
            existing = thuchi_collection.find_one({
                'user_id': update.effective_user.id,
                'month': current_month
            })
            
            if not existing:
                await update.message.reply_text('❌ Bạn chưa nhập số tiền ban đầu cho tháng này!')
                await show_menu(update)
                return
            
            # Get category for expense
            category = get_expense_category(description)
            
            # Insert expense record
            thuchi_collection.insert_one({
                'user_id': update.effective_user.id,
                'month': current_month,
                'so_tien': -amount,  # Negative for expenses
                'mo_ta': description,
                'danh_muc': category,
                'created_at': datetime.now()
            })
            
            # Update balance
            thuchi_collection.update_one(
                {'user_id': update.effective_user.id, 'month': current_month},
                {'$inc': {'so_tien': -amount}}
            )
            
            # Get updated balance
            updated = thuchi_collection.find_one({
                'user_id': update.effective_user.id,
                'month': current_month
            })
            
            # Send confirmation message
            message = f'✅ Đã ghi nhận chi tiêu:\n\n'
            message += f'💰 Số tiền: {amount:,}đ\n'
            message += f'📝 Mô tả: {description}\n'
            message += f'🏷️ Danh mục: {CATEGORY_EMOJIS.get(category, "📌")} {category}\n'
            message += f'💎 Số dư còn lại: {updated["so_tien"]:,}đ'
            
            await update.message.reply_text(message)
            await show_menu(update)
            
        except ValueError:
            pass  # Ignore messages that don't match the expense format

async def nhap_tien_ban_dau(update: Update, context: ContextTypes.DEFAULT_TYPE, so_tien: int):
    """Nhập số tiền ban đầu."""
    user_id = update.effective_user.id
    current_month = datetime.now().strftime('%Y-%m')
    
    # Get user's collection
    thuchi_collection = get_user_collection(user_id)
    
    # Check if already exists
    existing = thuchi_collection.find_one({
        'user_id': user_id,
        'month': current_month
    })
    
    if existing:
        await update.message.reply_text('❌ Bạn đã nhập số tiền ban đầu cho tháng này rồi!')
        return
    
    # Insert new record
    thuchi_collection.insert_one({
        'user_id': user_id,
        'month': current_month,
        'so_tien': so_tien,
        'created_at': datetime.now()
    })
    
    await update.message.reply_text(f'✅ Đã nhập số tiền ban đầu: {so_tien:,}đ')

async def them_tien(update: Update, context: ContextTypes.DEFAULT_TYPE, so_tien: int):
    """Thêm tiền vào số dư."""
    user_id = update.effective_user.id
    current_month = datetime.now().strftime('%Y-%m')
    
    # Get user's collection
    thuchi_collection = get_user_collection(user_id)
    
    # Check if exists
    existing = thuchi_collection.find_one({
        'user_id': user_id,
        'month': current_month
    })
    
    if not existing:
        await update.message.reply_text('❌ Bạn chưa nhập số tiền ban đầu cho tháng này!')
        return
    
    # Update balance
    thuchi_collection.update_one(
        {'user_id': user_id, 'month': current_month},
        {'$inc': {'so_tien': so_tien}}
    )
    
    await update.message.reply_text(f'✅ Đã thêm {so_tien:,}đ vào số dư')

async def xem_so_du(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem số dư hiện tại."""
    user_id = update.effective_user.id
    current_month = datetime.now().strftime('%Y-%m')
    
    # Get user's collection
    thuchi_collection = get_user_collection(user_id)
    
    # Get current balance
    record = thuchi_collection.find_one({
        'user_id': user_id,
        'month': current_month
    })
    
    if not record:
        message = '❌ Bạn chưa nhập số tiền ban đầu cho tháng này!'
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return
    
    # Calculate total expenses
    chi_tieu = list(thuchi_collection.find({
        'user_id': user_id,
        'month': current_month,
        'so_tien': {'$lt': 0}
    }))
    tong_chi_tieu = sum(ct['so_tien'] for ct in chi_tieu)
    
    # Calculate remaining balance
    so_du = record['so_tien'] + tong_chi_tieu
    
    message = f'💰 Số dư tháng {current_month}:\n\n'
    message += f'💵 Số tiền ban đầu: {record["so_tien"]:,}đ\n'
    message += f'💸 Tổng chi tiêu: {abs(tong_chi_tieu):,}đ\n'
    message += f'💎 Số dư còn lại: {so_du:,}đ'
    
    if update.message:
        await update.message.reply_text(message)
    else:
        await update.callback_query.message.reply_text(message)

async def xem_chi_tieu_theo_thang(update: Update, context: ContextTypes.DEFAULT_TYPE, month_str: str):
    """Xem chi tiêu theo tháng."""
    user_id = update.effective_user.id
    
    # Get user's collection
    thuchi_collection = get_user_collection(user_id)
    
    # Get expenses for the month
    chi_tieu = list(thuchi_collection.find({
        'user_id': user_id,
        'month': month_str,
        'so_tien': {'$lt': 0}
    }))
    
    if not chi_tieu:
        message = f'📊 Chưa có chi tiêu nào trong tháng {month_str}!'
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return
    
    # Calculate total expenses
    tong_chi_tieu = sum(ct['so_tien'] for ct in chi_tieu)
    
    # Group expenses by category
    chi_tieu_theo_danh_muc = {}
    for ct in chi_tieu:
        danh_muc = ct.get('danh_muc', 'Khác')
        if danh_muc in chi_tieu_theo_danh_muc:
            chi_tieu_theo_danh_muc[danh_muc] += ct['so_tien']
        else:
            chi_tieu_theo_danh_muc[danh_muc] = ct['so_tien']
    
    message = f'📊 Chi tiêu tháng {month_str}:\n\n'
    message += f'💵 Tổng chi tiêu: {abs(tong_chi_tieu):,}đ\n\n'
    message += '📝 Chi tiết theo danh mục:\n'
    
    # Sort by amount
    sorted_chi_tieu = sorted(chi_tieu_theo_danh_muc.items(), key=lambda x: x[1])
    for danh_muc, so_tien in sorted_chi_tieu:
        emoji = CATEGORY_EMOJIS.get(danh_muc, '📌')
        phan_tram = (abs(so_tien) / abs(tong_chi_tieu)) * 100
        message += f'{emoji} {danh_muc}: {abs(so_tien):,}đ ({phan_tram:.1f}%)\n'
    
    if update.message:
        await update.message.reply_text(message)
    else:
        await update.callback_query.message.reply_text(message)

async def phan_tich_chi_tieu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Phân tích chi tiêu trong tháng."""
    user_id = update.effective_user.id
    current_month = datetime.now().strftime('%Y-%m')
    
    # Get user's collection
    thuchi_collection = get_user_collection(user_id)
    
    chi_tieu = list(thuchi_collection.find({
        'user_id': user_id,
        'month': current_month,
        'so_tien': {'$lt': 0}
    }))
    
    if not chi_tieu:
        message = '📊 Chưa có chi tiêu nào trong tháng này!'
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return
    
    # Calculate total expenses
    tong_chi_tieu = sum(ct['so_tien'] for ct in chi_tieu)
    
    # Group expenses by category
    chi_tieu_theo_danh_muc = {}
    for ct in chi_tieu:
        danh_muc = ct.get('danh_muc', 'Khác')
        if danh_muc in chi_tieu_theo_danh_muc:
            chi_tieu_theo_danh_muc[danh_muc] += ct['so_tien']
        else:
            chi_tieu_theo_danh_muc[danh_muc] = ct['so_tien']
    
    message = '📊 Phân tích chi tiêu tháng này:\n\n'
    message += f'💵 Tổng chi tiêu: {abs(tong_chi_tieu):,}đ\n\n'
    message += '📝 Chi tiết theo danh mục:\n'
    
    # Sort by amount
    sorted_chi_tieu = sorted(chi_tieu_theo_danh_muc.items(), key=lambda x: x[1], reverse=True)
    for danh_muc, so_tien in sorted_chi_tieu:
        emoji = CATEGORY_EMOJIS.get(danh_muc, '📌')
        phan_tram = (abs(so_tien) / abs(tong_chi_tieu)) * 100
        message += f'{emoji} {danh_muc}: {abs(so_tien):,}đ ({phan_tram:.1f}%)\n'
    
    # Create pie chart
    plt.figure(figsize=(10, 8))
    plt.clf()
    
    # Prepare data for pie chart
    labels = []
    sizes = []
    colors = ['#FF9999', '#66B2FF', '#99FF99', '#FFCC99', '#FF99CC', '#99FFCC', '#FFB366', '#99CCE6', '#FFB3B3']
    
    for danh_muc, so_tien in sorted_chi_tieu:
        phan_tram = (abs(so_tien) / abs(tong_chi_tieu)) * 100
        if phan_tram >= 3:  # Only show categories with >= 3%
            labels.append(f'{danh_muc}\n({phan_tram:.1f}%)')
            sizes.append(abs(so_tien))
    
    # Draw pie chart
    plt.pie(sizes, labels=labels, colors=colors[:len(sizes)], autopct='', startangle=90)
    plt.title(f'Phân bố chi tiêu tháng {current_month}')
    
    # Save chart to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    
    # Send text message
    if update.message:
        await update.message.reply_text(message)
        await update.message.reply_photo(buf)
    else:
        await update.callback_query.message.reply_text(message)
        await update.callback_query.message.reply_photo(buf)
    
    # Close figure to free memory
    plt.close()

async def tong_hop_chi_tieu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tổng hợp chi tiêu trong tháng."""
    user_id = update.effective_user.id
    current_month = datetime.now().strftime('%Y-%m')
    
    # Get user's collection
    thuchi_collection = get_user_collection(user_id)
    
    # Get all expenses for the month
    chi_tieu = list(thuchi_collection.find({
        'user_id': user_id,
        'month': current_month,
        'so_tien': {'$lt': 0}
    }).sort('created_at', -1))  # Sắp xếp theo thời gian mới nhất
    
    if not chi_tieu:
        message = f'📊 Chưa có chi tiêu nào trong tháng {current_month}!'
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return
    
    # Calculate total expenses
    tong_chi_tieu = sum(ct['so_tien'] for ct in chi_tieu)
    
    # Group expenses by category
    chi_tieu_theo_danh_muc = {}
    for ct in chi_tieu:
        danh_muc = ct.get('danh_muc', 'Khác')
        if danh_muc in chi_tieu_theo_danh_muc:
            chi_tieu_theo_danh_muc[danh_muc] += ct['so_tien']
        else:
            chi_tieu_theo_danh_muc[danh_muc] = ct['so_tien']
    
    # Create message
    message = f'📊 Tổng hợp chi tiêu tháng {current_month}:\n\n'
    message += f'💵 Tổng chi tiêu: {abs(tong_chi_tieu):,}đ\n\n'
    message += '📝 Chi tiết theo danh mục:\n'
    
    # Sort categories by amount
    sorted_chi_tieu = sorted(chi_tieu_theo_danh_muc.items(), key=lambda x: x[1], reverse=True)
    for danh_muc, so_tien in sorted_chi_tieu:
        emoji = CATEGORY_EMOJIS.get(danh_muc, '📌')
        phan_tram = (abs(so_tien) / abs(tong_chi_tieu)) * 100
        message += f'{emoji} {danh_muc}: {abs(so_tien):,}đ ({phan_tram:.1f}%)\n'
    
    message += '\n📋 Danh sách chi tiêu:\n'
    
    # Group expenses by date
    chi_tieu_theo_ngay = {}
    for ct in chi_tieu:
        ngay = ct['created_at'].strftime('%d/%m/%Y')
        if ngay not in chi_tieu_theo_ngay:
            chi_tieu_theo_ngay[ngay] = {
                'chi_tieu': [],
                'tong': 0
            }
        chi_tieu_theo_ngay[ngay]['chi_tieu'].append(ct)
        chi_tieu_theo_ngay[ngay]['tong'] += ct['so_tien']
    
    # Sort dates in descending order
    for ngay in sorted(chi_tieu_theo_ngay.keys(), reverse=True):
        message += f'\n📅 {ngay} - Tổng: {abs(chi_tieu_theo_ngay[ngay]["tong"]):,}đ\n'
        for ct in chi_tieu_theo_ngay[ngay]['chi_tieu']:
            emoji = CATEGORY_EMOJIS.get(ct.get('danh_muc', 'Khác'), '📌')
            gio = ct['created_at'].strftime('%H:%M')
            message += f'  • {gio} - {emoji} {ct["mo_ta"]}: {abs(ct["so_tien"]):,}đ\n'
    
    if update.message:
        await update.message.reply_text(message)
    else:
        await update.callback_query.message.reply_text(message)

async def them_tu_khoa(update: Update, context: ContextTypes.DEFAULT_TYPE, tu_khoa: str, danh_muc: str):
    """Thêm từ khóa mới."""
    # Kiểm tra xem từ khóa đã tồn tại chưa
    existing = tu_khoa_collection.find_one({'tu_khoa': tu_khoa.lower()})
    if existing:
        await update.message.reply_text(
            f'❌ Từ khóa "{tu_khoa}" đã tồn tại trong danh mục {existing["danh_muc"]}'
        )
        return

    # Thêm từ khóa mới
    tu_khoa_collection.insert_one({
        'tu_khoa': tu_khoa.lower(),
        'danh_muc': danh_muc,
        'ngay_tao': datetime.now()
    })

    emoji = CATEGORY_EMOJIS.get(danh_muc, '📌')
    await update.message.reply_text(
        f'✅ Đã thêm từ khóa mới:\n\n'
        f'🔤 Từ khóa: {tu_khoa}\n'
        f'{emoji} Danh mục: {danh_muc}'
    )

async def xem_tu_khoa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem danh sách từ khóa theo danh mục."""
    # Lấy tất cả từ khóa và nhóm theo danh mục
    tu_khoa_theo_danh_muc = {}
    all_keywords = list(tu_khoa_collection.find().sort('danh_muc'))
    
    for keyword in all_keywords:
        danh_muc = keyword['danh_muc']
        if danh_muc not in tu_khoa_theo_danh_muc:
            tu_khoa_theo_danh_muc[danh_muc] = []
        tu_khoa_theo_danh_muc[danh_muc].append(keyword['tu_khoa'])
    
    if not tu_khoa_theo_danh_muc:
        message = '❌ Chưa có từ khóa nào được thêm vào!'
        if update.message:
            await update.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(message)
        return

    # Tạo danh sách tin nhắn, mỗi tin nhắn chứa một số danh mục
    messages = []
    current_message = '📝 Danh sách từ khóa theo danh mục:\n\n'
    
    for danh_muc, tu_khoa_list in tu_khoa_theo_danh_muc.items():
        emoji = CATEGORY_EMOJIS.get(danh_muc, '📌')
        category_text = f'{emoji} {danh_muc}:\n'
        category_text += '  • ' + '\n  • '.join(sorted(tu_khoa_list)) + '\n\n'
        
        # Nếu tin nhắn hiện tại + danh mục mới vượt quá giới hạn, tạo tin nhắn mới
        if len(current_message) + len(category_text) > 4000:
            messages.append(current_message)
            current_message = '📝 Danh sách từ khóa theo danh mục (tiếp):\n\n'
        
        current_message += category_text
    
    # Thêm tin nhắn cuối cùng vào danh sách
    if current_message:
        messages.append(current_message)
    
    # Gửi từng tin nhắn
    for msg in messages:
        if update.message:
            await update.message.reply_text(msg)
        else:
            await update.callback_query.message.reply_text(msg)

async def xoa_tu_khoa(update: Update, context: ContextTypes.DEFAULT_TYPE, tu_khoa: str):
    """Xóa từ khóa."""
    result = tu_khoa_collection.find_one_and_delete({'tu_khoa': tu_khoa.lower()})
    
    if result:
        emoji = CATEGORY_EMOJIS.get(result['danh_muc'], '📌')
        await update.message.reply_text(
            f'✅ Đã xóa từ khóa:\n\n'
            f'🔤 Từ khóa: {tu_khoa}\n'
            f'{emoji} Danh mục: {result["danh_muc"]}'
        )
    else:
        await update.message.reply_text(f'❌ Không tìm thấy từ khóa "{tu_khoa}"')

async def xoa_du_lieu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xóa toàn bộ dữ liệu của người dùng."""
    user_id = update.effective_user.id
    
    try:
        # Get user's collection
        thuchi_collection = get_user_collection(user_id)
        
        # Delete all records
        result = thuchi_collection.delete_many({'user_id': user_id})
        
        if result.deleted_count > 0:
            await update.message.reply_text(f'✅ Đã xóa {result.deleted_count} bản ghi chi tiêu của bạn!')
        else:
            await update.message.reply_text('❌ Không có dữ liệu nào để xóa!')
            
    except Exception as e:
        await update.message.reply_text(f'❌ Lỗi khi xóa dữ liệu: {str(e)}')

async def xoa_du_lieu_theo_ngay(update: Update, context: ContextTypes.DEFAULT_TYPE, ngay: str):
    """Xóa dữ liệu theo ngày cụ thể."""
    user_id = update.effective_user.id
    
    try:
        # Parse date
        ngay_obj = datetime.strptime(ngay, '%d/%m/%Y')
        ngay_str = ngay_obj.strftime('%Y-%m-%d')
        
        # Get user's collection
        thuchi_collection = get_user_collection(user_id)
        
        # Delete records for the specified date
        result = thuchi_collection.delete_many({
            'user_id': user_id,
            'created_at': {
                '$gte': datetime.combine(ngay_obj, datetime.min.time()),
                '$lt': datetime.combine(ngay_obj, datetime.max.time())
            }
        })
        
        if result.deleted_count > 0:
            await update.message.reply_text(f'✅ Đã xóa {result.deleted_count} bản ghi chi tiêu ngày {ngay}!')
        else:
            await update.message.reply_text(f'❌ Không có dữ liệu nào để xóa cho ngày {ngay}!')
            
    except ValueError:
        await update.message.reply_text('❌ Định dạng ngày không hợp lệ. Vui lòng sử dụng định dạng DD/MM/YYYY')
    except Exception as e:
        await update.message.reply_text(f'❌ Lỗi khi xóa dữ liệu: {str(e)}')

def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main() 