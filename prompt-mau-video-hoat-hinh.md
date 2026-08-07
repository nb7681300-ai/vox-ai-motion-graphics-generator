# PROMPT MẪU — Tạo kịch bản + demo hoạt hình HTML cho video "Người Que / Flat Vector"

> **Cách dùng:** Copy nguyên văn khối prompt bên dưới và gửi cho Claude, KHÔNG cần sửa gì cả.
> Mỗi lần chạy, Claude sẽ tự chọn/tự nghĩ ra một câu chuyện ngụ ngôn khác (khác với các lần
> chạy trước) và tự điền toàn bộ thông tin nhân vật, bối cảnh, thông điệp — bạn không cần
> ngồi thay tên truyện hay nội dung thủ công nữa. Không cần đính kèm file mẫu.

---

## PROMPT (copy từ đây)

```
Hãy đóng vai một đạo diễn hoạt hình + lập trình viên front-end, tạo cho tôi 2 file
để sản xuất một video hoạt hình ngắn theo đúng khuôn mẫu kỹ thuật bên dưới:

1. content.md — kịch bản phân cảnh chi tiết (dạng văn bản/Markdown)
2. animation.html — file HTML/CSS/JS demo hoạt hình minh họa cho kịch bản đó,
   tự chạy timeline theo đúng lời bình và thời lượng trong content.md

=== HỎI ĐỘ DÀI TRƯỚC KHI BẮT ĐẦU (BẮT BUỘC) ===
Trước khi làm bất kỳ việc gì khác (kể cả chọn truyện), PHẢI hỏi tôi trước 1 câu duy nhất:
"Bạn muốn video dài bao nhiêu phút?" (cho tôi nhập một con số, ví dụ nhập 3 nghĩa là 3 phút).
Chỉ sau khi tôi trả lời số phút, mới tiến hành các bước tiếp theo. Không tự ý mặc định 60 giây
nếu tôi chưa trả lời câu hỏi này (trừ khi tôi đã nêu rõ độ dài mong muốn ngay trong tin nhắn gửi
kèm prompt, ví dụ đã ghi sẵn "3 phút" hoặc "180 giây" — khi đó không cần hỏi lại, dùng luôn số đó).

Sau khi có số phút (gọi là M), tính toán lại toàn bộ thông số kỹ thuật:
- Tổng thời lượng TOTAL (giây) = M × 60
- Mỗi cảnh vẫn giữ độ dài trong khoảng 6–12 giây (ưu tiên ~8–10 giây/cảnh cho dễ theo dõi)
- Số cảnh N = làm tròn TOTAL / (độ dài trung bình mỗi cảnh đã chọn), sao cho tổng thời lượng
  các cảnh cộng lại khớp đúng TOTAL (giây cuối cùng có thể co giãn nhẹ ở cảnh kết để làm tròn)
- Nếu M lớn (video dài, ví dụ trên 2 phút / nhiều hơn ~12-14 cảnh): vẫn giữ cấu trúc truyện
  rõ ràng (Mở đầu → Diễn biến → Cao trào → Kết + Thông điệp), có thể chia diễn biến thành nhiều
  cảnh nhỏ hơn để câu chuyện không bị dồn nén hay lặp ý, và có thể chèn thêm tình tiết phụ hợp lý
  để câu chuyện đủ "dày" cho thời lượng dài hơn, chứ không kéo dài một tình tiết bằng cách lặp lại.
- Nếu M rất ngắn (dưới 1 phút, ví dụ 0.5 phút/30 giây): có thể giảm số cảnh xuống 4–5 cảnh,
  vẫn phải giữ đủ Mở đầu – Diễn biến – Kết + Thông điệp, không được cắt bỏ cảnh kết/thông điệp.
- Luôn cập nhật lại mọi chỗ có liên quan đến số "60 giây" và "7 cảnh" trong các mục dưới đây
  (tiêu đề content.md, khối thông tin đầu bài, mốc thời gian từng cảnh, biến TOTAL trong JS,
  #timer hiển thị "X.Xs / [TOTAL]s", mảng scenes...) theo đúng M và N vừa tính được.

=== TỰ CHỌN CÂU CHUYỆN (Claude tự quyết định, không cần tôi cung cấp) ===
Trước khi viết, hãy TỰ CHỌN một câu chuyện ngụ ngôn/cổ tích mang tính giáo dục phù hợp trẻ em
(có thể là truyện ngụ ngôn dân gian Việt Nam, truyện ngụ ngôn Aesop quen thuộc, hoặc một câu
chuyện HOÀN TOÀN NGUYÊN BẢN do bạn tự sáng tác) theo các nguyên tắc sau:

- Mỗi lần chạy prompt này, hãy chọn MỘT câu chuyện KHÁC với những lần trước trong cùng
  cuộc trò chuyện này (nếu là lần đầu, chọn tự do). Đừng lặp lại truyện đã dùng.
- Ưu tiên đa dạng: xen kẽ giữa truyện dân gian quen thuộc (Rùa và Thỏ, Cáo và Chùm Nho,
  Kiến và Châu Chấu, Chó Sói và Cừu Non, Sư Tử và Chuột Nhắt, Ve và Kiến, Cây Tre Trăm Đốt,
  Sự Tích Trầu Cau, Ăn Khế Trả Vàng, Thạch Sanh, Cáo Đội Lốt Hổ...) và ý tưởng tự sáng tác mới.
- Câu chuyện phải có: 1 bài học đạo đức/kỹ năng sống rõ ràng, phù hợp trẻ em (trung thực,
  kiên trì, chia sẻ, khiêm tốn, đoàn kết, dũng cảm, biết ơn, không tham lam, giữ lời hứa,
  tôn trọng người khác...), tối đa 2-3 nhân vật chính để dễ dựng hoạt hình đơn giản, và một
  bối cảnh cụ thể, dễ vẽ bằng hình khối SVG cơ bản (rừng, ao, làng quê, biển, núi, sân trường...).
- Tự đặt tên truyện, xây dựng nhân vật (tên, 1 câu tính cách), nhân vật phụ nếu cần, bối cảnh,
  và thông điệp/câu tục ngữ liên quan — KHÔNG hỏi lại tôi, tự quyết định toàn bộ rồi bắt tay viết.
- Thông số kỹ thuật mặc định (chỉ đổi nếu tôi nêu rõ yêu cầu khác trong tin nhắn):
  Thời lượng 60 giây · 7 cảnh, mỗi cảnh 6–12 giây · Tỉ lệ khung hình 16:9.
- Ở đầu câu trả lời (trước khi đưa 2 file), nói ngắn gọn 1 câu bạn đã chọn truyện nào và
  bài học là gì, để tôi biết Claude đã chọn chuyện gì mà không cần mở file.

=== YÊU CẦU CHO content.md ===
Viết theo đúng cấu trúc sau (giữ nguyên thứ tự các mục):

1. Tiêu đề: "KỊCH BẢN VIDEO HOẠT HÌNH NGƯỜI QUE" + tên truyện + chủ đề bài học
2. Khối thông tin đầu bài gồm: Thời lượng, Định dạng (hoạt hình 2D tối giản,
   flat vector, nét vẽ đơn giản), Nhân vật (liệt kê từng nhân vật + 1 dòng tính cách),
   Bối cảnh, Thông điệp (nêu rõ, có thể kèm câu thành ngữ/tục ngữ liên quan)
3. "BẢNG PHÂN CẢNH CHI TIẾT" — chia thành N cảnh theo mốc thời gian
   (ví dụ 0:00–0:08, 0:08–0:16 ...). Mỗi cảnh trình bày đúng 4 mục:
   - **Hình ảnh:** mô tả bố cục, vị trí nhân vật, biểu cảm, đạo cụ trong khung hình
   - **Hoạt động:** liệt kê CHÍNH XÁC các chuyển động hoạt hình cần animate
     (ví dụ: "Thỏ animate chạy siêu nhanh (chân blur)", "mai rùa lắc nhẹ theo nhịp bước",
     "chữ 'Zzz' fade in/out và bay lên cao dần") — vì đây sẽ là cơ sở để dựng CSS animation
   - **Lời bình (voice-over):** câu thoại/dẫn chuyện đúng với cảnh đó, đặt trong dấu ngoặc kép,
     văn phong kể chuyện thiếu nhi, có thể có hội thoại trực tiếp giữa nhân vật
   - **Âm thanh:** mô tả nhạc nền + hiệu ứng âm thanh gợi ý cho từng cảnh
     (nhạc nền phải "chuyển tông theo cảm xúc" qua các cảnh)
4. Cảnh cuối cùng luôn là cảnh "KẾT — THÔNG ĐIỆP": chữ thông điệp hiện lên giữa khung hình
   (fade-in + scale nhẹ), nhân vật chính đứng vẫy chào, có ánh nắng/khung cảnh ấm áp,
   lời bình nhắc lại bài học một cách trực tiếp, gần gũi với trẻ em
5. Mục "GHI CHÚ SẢN XUẤT" ở cuối file, gồm:
   - Phong cách hình ảnh (flat design, bo tròn, palette màu pastel tươi sáng — gợi ý bảng màu cụ thể)
   - Font chữ phụ đề
   - Mô tả nhạc nền và cách nó biến đổi qua từng cảnh (liệt kê tóm tắt cảm xúc từng cảnh)
   - Tỷ lệ khung hình đề xuất
   - Tổng thời lượng, số cảnh, thời lượng trung bình mỗi cảnh
   - Một dòng ghi chú rằng file animation.html minh họa được đính kèm riêng

=== YÊU CẦU CHO animation.html (PHẢI GIỐNG HỆT CẤU TRÚC KỸ THUẬT SAU) ===
Đây là 1 file HTML độc lập (không phụ thuộc file ngoài, có thể mở trực tiếp bằng trình duyệt),
gồm 3 phần: CSS trong <style>, SVG scenes trong <body>, JS điều khiển timeline trong <script>.

A. CẤU TRÚC TỔNG THỂ (giữ nguyên id/class quan trọng để logic JS hoạt động):
   - #stage-wrap > #frame (aspect-ratio 16:9, bo góc, khung viền đậm, box-shadow, nền tối #111
     bao quanh để nổi bật khung hình như "màn hình")
   - Bên trong #frame:
     - #topbar: gồm #scene-tag (hiển thị "Cảnh X/N") và #progress-track > #progress-bar
       (thanh tiến trình chạy theo thời gian thực)
     - N div .scene (mỗi div id="sceneN"), mỗi cái chứa 1 <svg viewBox="0 0 800 450">
       vẽ toàn bộ nhân vật/bối cảnh cảnh đó bằng SVG thuần (path/circle/ellipse/line/rect/text),
       phong cách "người que" hình khối đơn giản, tất cả tô màu bằng CSS variables khai báo ở :root
       (không dùng ảnh bên ngoài, không dùng thư viện, chỉ SVG code tay)
     - Chỉ 1 .scene có class "active" tại một thời điểm (điều khiển bởi JS), các cảnh khác
       opacity:0, transition mượt khi chuyển cảnh
     - #caption ở dưới cùng, hiển thị lời bình hiện tại (span nền tối, chữ sáng, bo góc)
   - #controls bên dưới #frame: nút "⟲ Phát lại", nút "⏸ Tạm dừng"/"▶ Tiếp tục", và #timer
     hiển thị "X.Xs / 60s"

B. BẢNG MÀU (:root CSS variables) — định nghĩa palette pastel riêng phù hợp bối cảnh câu chuyện
   (ví dụ nếu truyện diễn ra trong rừng: --sky-1, --sky-2, --path, --line, màu riêng cho từng
   nhân vật, --accent cho điểm nhấn, --card cho nền thẻ chữ). Dùng nhất quán các biến này
   trong toàn bộ SVG, không hard-code màu rời rạc.

B2. FONT CHỮ TIẾNG VIỆT (BẮT BUỘC — tránh lỗi vỡ dấu/font) :
   - TUYỆT ĐỐI KHÔNG dùng "Trebuchet MS" làm font chính hoặc font fallback đầu tiên — font này
     hiển thị sai/vỡ dấu tiếng Việt (đặc biệt các dấu kép như ẫ, ặ, ẽ, ữ...) trên nhiều trình duyệt/hệ điều hành.
   - Font-family chuẩn cần dùng cho toàn bộ file (cả CSS body lẫn mọi thẻ SVG <text>):
     font-family: 'Segoe UI', 'Arial', 'Helvetica Neue', 'Noto Sans', sans-serif;
     (đây là các font hệ thống hỗ trợ đầy đủ bảng chữ cái tiếng Việt có dấu, không cần tải font ngoài
     vì file phải chạy độc lập, không phụ thuộc mạng).
   - Khai báo font-family này ở SELECTOR GỐC (html, body, và riêng cả thẻ `svg` hoặc `text` trong CSS)
     — KHÔNG chỉ khai báo ở `body`, vì thẻ <text> bên trong SVG không tự động kế thừa font từ CSS
     ngoài ở một số trình duyệt/trình render, dẫn đến chữ trong SVG bị đổi sang font serif mặc định
     và vỡ dấu. Ví dụ bắt buộc thêm vào CSS:
       svg text, text { font-family: 'Segoe UI','Arial','Helvetica Neue','Noto Sans',sans-serif; }
   - Với mọi thẻ `<text>` viết trực tiếp trong SVG (ví dụ chữ "Zzz", câu thoại "Ôi không!", thông điệp
     kết truyện...), nếu cần chắc chắn 100% không bị trình duyệt override, có thể thêm thuộc tính
     font-family="Segoe UI, Arial, Helvetica Neue, Noto Sans, sans-serif" ngay trên chính thẻ <text> đó,
     song song với khai báo CSS ở trên (double-safe).
   - Kiểm tra lại toàn bộ chữ tiếng Việt có dấu trong file (lời thoại, "Zzz", thông điệp kết,
     "Cảnh X/N", nhãn nút bấm...) để đảm bảo không ký tự nào bị thay bằng ô vuông (□) hoặc mất dấu.

C. HOẠT ẢNH CSS (@keyframes) — với MỖI hành động đã liệt kê trong mục "Hoạt động" của content.md,
   tạo một class + @keyframes tương ứng, đặt tên rõ nghĩa theo mẫu:
   [nhân-vật]-[hành-động] (ví dụ: .rabbit-bounce, .turtle-blink, .mouth-laugh, .head-nod,
   .flag-wave, .rabbit-run + .dust, .chest-breathe, .zzz (kèm .zzz2/.zzz3 với animation-delay
   để lặp so le), .turtle-walk, .finish-bounce, .cheer-arm, .fade-in-text, .sun-glow, .star-twinkle...).
   Nguyên tắc dựng animation:
   - Chuyển động lặp vô hạn (đi bộ, thở, nháy mắt, vẫy tay...): animation: ... infinite
   - Chuyển động một lần theo tiến trình cảnh (chạy vọt đi, về đích...): animation: ... forwards,
     dùng translateX/translateY để dịch chuyển nhân vật ngang qua khung hình
   - Luôn khai báo transform-origin hợp lý theo toạ độ khớp nối (vai, chân, cổ...) để xoay tự nhiên
   - Timing: theo đúng độ dài của cảnh đó trong content.md (ví dụ cảnh dài 8s thì animation
     chạy đúng khoảng ~6-8s forwards để khớp)

C2. AN TOÀN KHUNG HÌNH — BẮT BUỘC (tránh lỗi nhân vật bị lệch/tràn ra ngoài khung hình):
   Đây là lỗi hay gặp nhất khi dựng SVG + translateX/translateY, nên phải tuân thủ chặt:
   - Toàn bộ viewBox cố định là "0 0 800 450". Coi đây là vùng an toàn, và luôn CHỪA LỀ
     tối thiểu 20–30px ở mọi cạnh (trái/phải/trên/dưới) — không đặt bất kỳ phần nào của
     nhân vật/chữ/đạo cụ chạm sát hoặc vượt quá 0, 800 (trục X) và 0, 450 (trục Y) tại BẤT KỲ
     thời điểm nào trong toàn bộ animation, không chỉ ở trạng thái đứng yên.
   - Với mọi <g transform="translate(x,y)"> có chứa animation translateX/translateY (chạy, bò,
     đi bộ...): PHẢI tính trước tọa độ điểm bắt đầu và điểm kết thúc trên trục thời gian, cộng
     thêm bán kính/độ rộng ước lượng của nhân vật (ví dụ nhân vật rộng ~90–100px thì tính nửa
     bề rộng ~45–50px mỗi bên), rồi kiểm tra:
       (tọa độ x gốc của <g>) + (khoảng translateX tối đa) + (nửa bề rộng nhân vật) <= 800 - lề an toàn
       (tọa độ x gốc của <g>) - (nửa bề rộng nhân vật) >= 0 + lề an toàn
     Áp dụng tương tự cho trục Y nếu có translateY. Nếu công thức vượt ngưỡng, PHẢI giảm khoảng
     translate hoặc dịch lại tọa độ transform gốc của <g> cho khớp, không được để mặc định.
   - Với animation dạng "nhân vật chạy/bò từ vạch xuất phát đến gần vạch đích": khoảng cách
     translate phải được tính sao cho vị trí CUỐI của nhân vật dừng lại ngay trước hoặc ngay
     tại vạch đích/mốc đã vẽ trong cùng cảnh đó (không chạy vọt ra ngoài viewBox), và vị trí
     BẮT ĐẦU không được âm hoặc nằm ngoài khung (ví dụ tránh transform gốc kiểu
     translate(-380px) rồi cộng animation translateX khiến nhân vật xuất phát từ ngoài khung hình
     — nếu cảnh cần thể hiện nhân vật "chạy vào khung hình từ mép trái", phải đảm bảo phần thân
     nhân vật vẫn nằm trong viewBox ngay từ frame đầu tiên của animation, không bị cắt cụt).
   - Với các phần tử tĩnh (không animate vị trí) như cây, mặt trời, sóc, chim, bảng chữ thông
     điệp...: kiểm tra tọa độ tâm + bán kính/kích thước không vượt biên viewBox trừ lề an toàn.
   - Sau khi viết xong mỗi cảnh, tự rà lại (mentally trace) toàn bộ animation của cảnh đó theo
     thời gian: tại 0%, 25%, 50%, 75%, 100% của mỗi animation, nhân vật có còn nằm gọn trong
     khung 800x450 (trừ lề) hay không. Nếu có nhân vật/chi tiết bị lệch ra ngoài ở bất kỳ mốc
     nào, phải điều chỉnh lại transform-origin, tọa độ gốc, hoặc khoảng cách translate trước khi
     đưa vào bản trả lời cuối cùng — đây là bước kiểm tra bắt buộc, không được bỏ qua.



D. LOGIC JS ĐIỀU KHIỂN TIMELINE (giữ nguyên cơ chế này):
   - Mảng `scenes` gồm N object {id, start (giây bắt đầu, khớp mốc thời gian trong content.md),
     text (đúng nguyên văn lời bình của cảnh đó, có thể có dấu ngoặc kép cho hội thoại)}
   - Biến TOTAL = tổng thời lượng (giây)
   - Dùng requestAnimationFrame để tick theo performance.now(), tính elapsed time,
     cập nhật progress bar + timer mỗi frame
   - Hàm activateScene(): gỡ class "active" khỏi mọi .scene, gán "active" cho cảnh hiện tại,
     cập nhật #caption-text và #scene-tag; chỉ gọi khi cảnh thay đổi (so sánh lastSceneId)
     để không re-trigger animation liên tục
   - Khi elapsed >= TOTAL: dừng lại ở cảnh cuối (giữ nguyên khung hình cuối, không loop tự động)
   - Nút "Phát lại": reset lastSceneId, reset startTime, chạy lại từ đầu
   - Nút "Tạm dừng/Tiếp tục": cancelAnimationFrame khi pause, cộng dồn thời gian đã pause
     khi resume để timeline không bị nhảy
   - Tự động play() ngay khi trang load

=== YÊU CẦU CHUNG ===
- Toàn bộ lời thoại, chú thích, nhãn trong SVG và caption phải bằng tiếng Việt có dấu.
- Văn phong content.md: kể chuyện thiếu nhi, gần gũi, có bài học đạo đức rõ ràng ở cuối.
- animation.html phải tự chạy được ngay khi mở file, không cần bước cài đặt gì thêm,
  không gọi API/font/thư viện ngoài — chỉ dùng font hệ thống sans-serif đã nêu ở mục B2
  (Segoe UI/Arial/Helvetica Neue/Noto Sans), KHÔNG dùng Trebuchet MS, để đảm bảo tiếng Việt
  hiển thị đúng dấu trên mọi máy.
- Đảm bảo animation.html thể hiện đúng — không thiếu — toàn bộ 7 cảnh (hoặc N cảnh) đã mô tả
  trong content.md, đồng bộ tuyệt đối về thời lượng, nhãn cảnh, và lời bình.
- TRƯỚC KHI đưa file animation.html ra, thực hiện bước rà soát cuối theo mục C2 (an toàn khung
  hình) cho TẤT CẢ các cảnh — đảm bảo không có nhân vật, chi tiết, hay chữ nào bị lệch/cắt/tràn
  ra ngoài viewBox 800x450 ở bất kỳ thời điểm nào trong animation.
- Sau khi tạo xong, đưa ra 2 file: content.md và animation.html.
```

---

## Ghi chú khi dùng lại prompt này

- **Không cần sửa gì trong prompt nữa.** Cứ copy-paste nguyên văn và gửi mỗi lần muốn có
  một câu chuyện mới — Claude sẽ tự chọn truyện, tự đặt tên nhân vật, bối cảnh, thông điệp.
- Nếu muốn "gợi ý" chủ đề thay vì để Claude tự do chọn hoàn toàn (ví dụ: muốn truyện về
  lòng dũng cảm, hoặc muốn nhân vật là loài vật dưới biển), chỉ cần thêm 1 dòng ngắn ngay
  sau khi paste prompt, ví dụ: *"Chủ đề mong muốn: lòng dũng cảm, bối cảnh dưới biển"* —
  Claude vẫn tự soạn toàn bộ phần còn lại.
- Nếu muốn đổi độ dài video (ví dụ 90 giây, 10 cảnh) hoặc đổi tỉ lệ khung hình (9:16 cho
  TikTok), thêm 1 dòng ghi chú tương tự, ví dụ: *"Thời lượng 90 giây, tỉ lệ 9:16"*.
- Nếu muốn tránh trùng với các truyện đã tạo ở những lần chat trước (không cùng cuộc hội
  thoại này), có thể liệt kê nhanh các tên truyện đã dùng để Claude né ra, ví dụ:
  *"Đã dùng: Rùa và Thỏ, Chiếc Rìu Vàng — đừng chọn lại 2 truyện này."*
- Nếu muốn phong cách hình ảnh khác "người que/flat vector" (ví dụ pixel art, giấy cắt dán...),
  thêm 1 dòng ghi chú phong cách — phần cấu trúc kỹ thuật (CSS variables, timeline JS...)
  vẫn áp dụng được.
