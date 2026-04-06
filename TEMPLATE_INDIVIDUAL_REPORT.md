# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Lương Trung Kiên
- **Student ID**: 2A202600473
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

*Đóng góp
Tham gia họp, đưa ra ý kiến, cùng làm với các bạn từ bước 0, viết một tool, đánh giá, tìm hiểu lỗi, và đưa ra hướng cải thiện.
Triển khai tool check_room_availability cho hệ thống ReAct agent trong bài toán đặt phòng khách sạn.
Tool này có nhiệm vụ kiểm tra tình trạng phòng trống dựa trên các tham số đầu vào như hotel_id, check-in và check-out. Tool có thể hoạt động trên dữ liệu giả lập (mock database) hoặc kết nối với nguồn dữ liệu thực tế.
Thiết kế interface của tool theo đúng định dạng structured output (JSON), đảm bảo tương thích với cơ chế tool-calling của agent (bao gồm name và args).
Tích hợp tool vào danh sách TOOLS của hệ thống, cho phép mô hình ngôn ngữ (LLM) có thể tự động lựa chọn và gọi tool khi cần xử lý các truy vấn liên quan đến kiểm tra phòng.*


- **Documentation**: Tool check_room_availability được tích hợp trực tiếp vào vòng lặp của ReAct agent như sau:

Trong mỗi vòng lặp, mô hình sẽ phân tích yêu cầu của người dùng và quyết định trả về một trong hai dạng: tool_call (gọi tool) hoặc final_answer (trả lời cuối cùng).
Khi mô hình xác định cần kiểm tra phòng, nó sẽ sinh ra một lời gọi tool với đầy đủ tham số (ví dụ: hotel_id, ngày nhận/trả phòng).
Hệ thống sẽ thực thi tool thông qua hàm run_tool(), sau đó nhận lại kết quả (ví dụ: còn phòng / hết phòng).
Kết quả này được đưa trở lại vào messages dưới dạng một tool_message, giúp mô hình “quan sát” được kết quả từ tool.
Dựa trên thông tin đó, mô hình có thể:
tiếp tục gọi tool khác (nếu cần), hoặc
đưa ra câu trả lời cuối cùng cho người dùng.

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Trong quá trình thử nghiệm, agent gặp lỗi khi thực hiện tool check_room_availability.
Cụ thể, log hiển thị dạng:

Action Input: {
  "hotel_id": "hotel_1",
  "dates": {
    "checkin": "2026-04-11",
    "checkout": "2026-04-12"
  }
}
Observation: ...
Final Answer: ...

Tuy nhiên, khi chạy riêng tool bằng file test (check_room_availability.py), kết quả trả về không khớp với kỳ vọng của agent (hoặc bị thiếu/khác format). Điều này khiến agent:

hiểu sai kết quả
hoặc không thể tiếp tục reasoning chính xác

- **Diagnosis**: Nguyên nhân chính đến từ sự không đồng bộ giữa output của tool và kỳ vọng của LLM trong ReAct loop, cụ thể:

Mismatch format dữ liệu:
Tool trả về dữ liệu không đúng schema mà model “hiểu” (ví dụ: thiếu field như available, rooms, hoặc format ngày khác).
Prompt chưa định nghĩa rõ output của tool:
Model không biết chính xác observation sẽ trông như thế nào → dẫn đến hiểu sai.
Thiếu ví dụ (few-shot) trong system prompt:
Model không được “học” cách xử lý kết quả từ tool → reasoning bị lệch.
Trong một số trường hợp, model có xu hướng:
suy đoán kết quả thay vì dựa vào observation
hoặc kết thúc sớm (final_answer) khi chưa đủ thông tin
- **Solution**: Chuẩn hóa output của tool, cải thiện system prompt, ràng buộc output của model, thêm logging chi tiết.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: So với chatbot truyền thống (trả lời trực tiếp), ReAct agent thể hiện khả năng suy luận tốt hơn nhờ vào block Thought.

Block Thought giúp mô hình chia nhỏ bài toán thành các bước hợp lý, thay vì cố gắng trả lời ngay lập tức.
Mô hình có thể xác định khi nào cần gọi tool, khi nào đã đủ thông tin để trả lời.
Điều này đặc biệt hữu ích trong các bài toán nhiều bước như booking (ví dụ: kiểm tra phòng → so sánh giá → đưa ra gợi ý).

Trong khi đó, chatbot thông thường:

Thường trả lời dựa trên kiến thức có sẵn → dễ bị hallucination (bịa thông tin).
Không có cơ chế suy luận rõ ràng từng bước.
2.  **Reliability**: Mặc dù mạnh hơn về reasoning, ReAct agent trong một số trường hợp lại hoạt động kém hơn chatbot truyền thống:

Tool lỗi hoặc trả dữ liệu sai → agent bị phụ thuộc hoàn toàn vào kết quả đó và có thể đưa ra kết luận sai.
Model chọn sai tool → dẫn đến reasoning sai ngay từ đầu.
Loop quá nhiều bước → có thể gây timeout hoặc không dừng đúng lúc.
Prompt chưa tốt → model có thể hiểu sai task và gọi tool không cần thiết.

Trong khi đó, chatbot truyền thống:

Đôi khi lại ổn định hơn trong các câu hỏi đơn giản, vì không phụ thuộc vào tool hay nhiều bước xử lý.
Trả lời nhanh hơn do không có vòng lặp.
3.  **Observation**: Observation (kết quả từ tool) đóng vai trò rất quan trọng trong ReAct agent:

Nó cung cấp feedback từ môi trường thực tế, giúp mô hình điều chỉnh bước tiếp theo.
Sau mỗi lần gọi tool, agent có thể:
xác nhận giả định ban đầu là đúng/sai
hoặc thay đổi chiến lược (ví dụ: chọn khách sạn khác nếu hết phòng)

Ví dụ:

Nếu check_room_availability trả về “hết phòng” → agent có thể chuyển sang tìm khách sạn khác.
Nếu còn phòng → agent có thể tiếp tục bước booking.

Không có observation:

Model chỉ suy luận “trong đầu” → dễ sai và không cập nhật thông tin mới.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**:Để triển khai hệ thống agent ở mức production, cần đảm bảo khả năng xử lý nhiều request đồng thời:

Sử dụng hàng đợi bất đồng bộ (asynchronous queue) như RabbitMQ hoặc Apache Kafka để xử lý các tool call, tránh block hệ thống khi có nhiều người dùng.
Tách riêng các thành phần:
LLM service
Tool execution service
Database
→ theo kiến trúc microservices để dễ scale độc lập.
Triển khai trên nền tảng container như Docker và orchestration bằng Kubernetes để tự động scale theo tải.
Sử dụng caching (ví dụ: kết quả weather hoặc search) để giảm số lần gọi tool lặp lại.
- **Safety**: Trong môi trường thực tế, cần kiểm soát hành vi của agent để tránh lỗi hoặc hành động không mong muốn:

Xây dựng một Supervisor LLM (mô hình giám sát) để:
kiểm tra tool call trước khi thực thi
phát hiện hành vi bất thường hoặc không hợp lệ
Áp dụng cơ chế validation input/output:
kiểm tra format args trước khi gọi tool
tránh injection hoặc dữ liệu sai
Thiết lập rule-based guardrails:
giới hạn số vòng lặp (max iterations)
whitelist các tool được phép gọi
Ghi log toàn bộ quá trình reasoning (thought, action, observation) để phục vụ audit và debug.
- **Performance**: Khi hệ thống có nhiều tool và dữ liệu lớn, cần tối ưu để giảm latency:

Sử dụng Vector Database như FAISS hoặc Pinecone để:
tìm kiếm tool phù hợp (tool retrieval)
hoặc hỗ trợ RAG cho agent
Áp dụng tool selection thông minh:
không đưa toàn bộ tool vào prompt
chỉ retrieve top-k tool liên quan → giảm token và tăng tốc độ
Sử dụng streaming response để trả lời từng phần cho người dùng thay vì chờ toàn bộ kết quả.
Tối ưu prompt và giới hạn context length để giảm chi phí và thời gian inference.

