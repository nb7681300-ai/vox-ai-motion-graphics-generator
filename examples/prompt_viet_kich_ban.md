# PROMPT HƯỚNG DẪN AI VIẾT KỊCH BẢN (DÙNG CHO CHATGPT/CLAUDE/GEMINI)

Bạn có thể copy đoạn prompt dưới đây gửi cho bất kỳ AI nào khi muốn tạo kịch bản mới cho công cụ generator này.

---

```text
Hãy viết một kịch bản hoạt hình ngắn theo các quy tắc cấu trúc nghiêm ngặt dưới đây để tôi có thể parse tự động bằng mã Python. Không thêm ký tự thoát "\" trước các dấu Markdown như #, **, >.

Cấu trúc file kịch bản (content.md) phải gồm 3 phần chính như sau:

---

## 1. TIÊU ĐỀ VÀ THÔNG TIN TỔNG QUAN (Đầu file)
- Tiêu đề câu chuyện phải nằm ở hàng đầu tiên sử dụng thẻ H1 (#). Bạn có thể viết thêm thông tin phụ sau dấu gạch ngang "—" hoặc trong dấu ngoặc đơn "()".
  Ví dụ: `# RÙA VÀ THỎ — Kịch bản lồng tiếng (Tổng thời lượng: 120 giây)`
- Phải có một dòng khai báo thông điệp ý nghĩa ở đầu hoặc cuối file bằng nhãn **Thông điệp cốt lõi:** hoặc sử dụng blockquote (>). Đây sẽ là nội dung xuất hiện trong file caption.txt.
  Ví dụ: `**Thông điệp cốt lõi:** Chậm mà chắc, kiên trì bền bỉ sẽ chiến thắng sự tự mãn.`

---

## 2. BẢNG PHÂN CẢNH CHI TIẾT (Chọn 1 trong 2 định dạng dưới đây)

### CÁCH 1: DẠNG BẢNG MARKDOWN (Khuyên Dùng - Rất trực quan và khó lỗi)
Bảng phải có ít nhất 4 cột và cột chứa nội dung giọng đọc thuyết minh bắt buộc phải có tên là "Lời bình" hoặc "Voice-over" hoặc "Thuyết minh".
Ví dụ:

| Cảnh | Thời lượng | Hình ảnh mô tả | Lời bình (Voice-over) | Ghi chú kỹ thuật |
|---|---|---|---|---|
| 1 | 0:00 – 0:18 (18s) | Mô tả hình ảnh tại đây... | "Ngày xưa, có một chú Thỏ chạy nhanh như gió..." | Ghi chú kỹ thuật tại đây... |
| 2 | 0:18 – 0:35 (17s) | Mô tả hình ảnh tại đây... | "Rùa nhìn thẳng vào mắt Thỏ..." | Ghi chú kỹ thuật tại đây... |

---

### CÁCH 2: DẠNG TIÊU ĐỀ PHÂN ĐOẠN (Dành cho kịch bản dạng viết xuôi)
Mỗi cảnh bắt buộc phải bắt đầu bằng tiêu đề thẻ H2 (##) kèm từ khóa "CẢNH N" và thời lượng dạng (Start - End) hoặc (Dur).
Phần thoại thuyết minh bắt buộc phải bắt đầu bằng nhãn `**Lời bình:**` hoặc `**Voice-over:**` (khuyên dùng định dạng blockquote `> "nội dung"` ở dòng tiếp theo).
Ví dụ:

## CẢNH 1 — Khu rừng buổi sáng (0:00 – 0:18 | 18s)
**Lời bình** (~13s):
> "Trong khu rừng xanh rợp bóng lá, có một chú Thỏ chạy nhanh như gió. Mỗi bước nhảy của Thỏ khiến bụi cỏ tung bay..."

**Hình ảnh:** Mô tả hình ảnh tại đây...

---

## 3. LƯU Ý QUAN TRỌNG:
1. Không chèn dấu gạch chéo ngược "\" trước các thẻ Markdown (ví dụ: viết `## CẢNH 1` chứ KHÔNG viết `\## CẢNH 1`).
2. Các dòng chỉ chứa thông số thời lượng hay ghi chú (như `(~13s):`) nếu viết ở cột Lời bình hoặc dòng Lời bình thì phải đặt ngoài dấu ngoặc kép hoặc blockquote của câu thoại thực tế.
3. Luôn ghi rõ thời lượng của mỗi cảnh dưới dạng `(start - end)` hoặc `(Xs)` để code tính toán chia khoảng thời gian khớp với file âm thanh.
```
