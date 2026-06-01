# 🙋‍♂️ CÁC CÂU HỎI THƯỜNG GẶP (FAQ)

Chào mừng anh em đã đến với kho Build Tweak & App của Đức Nguyen (1993). Dưới đây là tổng hợp các lỗi thường gặp và cách xử lý nhanh nhất khi sử dụng nguồn.

—

### 📌 1. Làm sao để thêm nguồn này vào Sileo / Feather?
* **Với Sileo (Tweak):** Mở Sileo -> Vào mục *Nguồn* -> Bấm *Thêm* -> Dán link: `https://username.github.io/ten-repo/`
* **Với Feather (App):** Mở Feather -> Chọn thêm nguồn Repository -> Dán link file json: `https://username.github.io/ten-repo/apps.json`

—

### ❌ 2. Tại sao tôi cài App qua Feather nhưng bị báo lỗi “Không thể xác minh”?
* **Nguyên nhân:** Do chứng chỉ (Certificate) miễn phí anh em đang dùng đã bị Apple thu hồi (Revoke).
* **Cách khắc phục:** Anh em cần xóa App cũ đi, cập nhật chứng chỉ mới (DNS/P12 sạch) trong Feather rồi tiến hành cài đặt lại nhé.

—

### 🛠️ 3. Tweak cài xong từ Sileo không hiển thị ngoài màn hình hoặc trong Cài đặt?
* **Cách 1:** Đảm bảo máy của bạn đã cài đặt các công cụ nền như `PreferenceLoader`, `AltList`, hoặc `RocketBootstrap`.
* **Cách 2:** Hãy thử **Respring** lại máy hoặc chạy lệnh `uicache` trong Terminal để làm mới biểu tượng.

—

### 📨 4. Tôi muốn yêu cầu cập nhật App/Tweak hoặc báo lỗi thì làm thế nào?
Anh em vui lòng vào mục **Issues** ngay trên Repo GitHub này, tạo một bài viết mới (New Issue) và mô tả rõ:
1. Tên Tweak/App bị lỗi.
2. Phiên bản iOS và thiết bị đang dùng.
3. Hình ảnh hoặc video quay lại lỗi (nếu có).

—
*Chúc anh em có những trải nghiệm vọc vạch máy vui vẻ!*