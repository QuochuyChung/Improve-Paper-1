# Trạng thái SWD391-19 - tích hợp báo cáo chính

Repo hiện chỉ có `swd391_topic1.pdf`, không có source LaTeX tạo ra PDF. PDF được
tạo bằng pdfTeX nhưng không chứa file đính kèm. Hai đầu vào bắt buộc được nêu trong
`task.md` cũng chưa có:

- `scoring_section.tex` (đầu ra Phần 1 / SWD391-12);
- `poc_section.tex` (đầu ra Phần 6 / SWD391-17).

Ngoài ra chưa có `scenario/logs/*.md` từ lần chạy thật trên homelab, nên chưa được
điền bất kỳ kết quả định lượng nào.

## Việc cần làm khi nhận đủ đầu vào

1. Đặt file source báo cáo chính và hai section trong cùng cây LaTeX.
2. Chèn `\input{scoring_section}` sau phần gap analysis/critical assessment phù hợp.
3. Chèn `\input{poc_section}` trước kết luận để tách rõ kết quả của paper và PoC của nhóm.
4. Bổ sung tài liệu tham khảo chỉ khi hai section mới có citation chưa tồn tại.
5. Biên dịch bằng pdfTeX (engine của PDF hiện tại), sửa riêng lỗi do hai section mới.
6. Kiểm tra reference, citation, hình, bảng, tiếng Việt và tràn lề trên bản render.
7. Tìm toàn bộ `CHƯA CÓ KẾT QUẢ THẬT`; chỉ thay từ `scenario/logs/*.md`, ghi tên log
   trong caption/note của bảng và giữ nguyên trạng thái `không đạt` nếu log ghi như vậy.

Không thể đánh dấu SWD391-19 hoàn tất cho đến khi các file trên được thêm vào repo.
