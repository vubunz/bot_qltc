# Bot Quản Lý Chi Tiêu 💰

Bot Telegram giúp quản lý chi tiêu cá nhân một cách hiệu quả và trực quan.
Link bot tác giả: https://t.me/quanlyti3n_bot

## Tính năng chính 🌟

- **Quản lý số dư** 💵

  - Nhập số tiền ban đầu
  - Thêm tiền vào số dư
  - Xem số dư hiện tại

- **Theo dõi chi tiêu** 📊

  - Ghi nhận chi tiêu tự động theo danh mục
  - Phân tích chi tiêu bằng biểu đồ
  - Xem chi tiêu theo tháng
  - Tổng hợp chi tiêu chi tiết

- **Quản lý từ khóa** 🔍

  - Tự động phân loại chi tiêu dựa trên từ khóa
  - Thêm/xóa/xem từ khóa theo danh mục
  - Chỉ admin mới có quyền quản lý từ khóa

- **Xóa dữ liệu** 🗑️
  - Xóa toàn bộ dữ liệu
  - Xóa dữ liệu theo ngày

## Cài đặt 🛠️

1. Clone repository:

```bash
git clone <repository_url>
cd bot_qltc
```

2. Cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt
```

3. Tạo file `.env` với các thông tin sau:

```
TELEGRAM_BOT_TOKEN=your_bot_token
MONGODB_URI=your_mongodb_uri
DATABASE_NAME=your_database_name
ADMIN_ID=your_telegram_user_id
```

4. Chạy bot:

```bash
python bot.py
```

## Cách sử dụng 📱

1. **Bắt đầu sử dụng**

   - Tìm bot trên Telegram
   - Gõ lệnh `/start` để bắt đầu

2. **Nhập chi tiêu**

   - Cú pháp: `<số tiền><k/tr> <mô tả>`
   - Ví dụ:
     - `50k ăn sáng`
     - `2.5tr tiền nhà`
     - `80k xăng`

3. **Các nút chức năng**
   - Nhập số tiền ban đầu
   - Thêm tiền
   - Xem số dư
   - Phân tích chi tiêu
   - Tổng hợp chi tiêu
   - Xem chi tiêu theo tháng

## Danh mục chi tiêu 📑

1. 🍴 Ăn uống
2. 🚗 Di chuyển
3. 🛍️ Mua sắm
4. 🎮 Giải trí
5. 💪 Sức khỏe
6. 📚 Học tập
7. 💅 Làm đẹp
8. 📝 Hóa đơn & Tiện ích
9. 📌 Khác

## Đóng góp 🤝

Nếu bạn thấy bot hữu ích, hãy ủng hộ tác giả một ly cà phê nhé! ☕️

## Liên hệ 📧

Nếu có bất kỳ câu hỏi hoặc góp ý nào, vui lòng liên hệ với tôi qua:

- Telegram: @vubunz
- Email: holongvu2002@gmail.com
