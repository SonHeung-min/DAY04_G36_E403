# Day 04 Lab v2 Report — Research Agent

## Team

- Team: G36
- Members: 
  - Vũ Hải Nam - 01173
  - Ong Xuân Sơn - 01327
  - Nguyễn Duy Dũng - 01505
  - Nguyễn Minh Nhật - 01131
  - Nguyễn Tiến Thành - 01539
  - Giang Minh Phú - 01729
- Provider/model: OpenAI / GPT-4o-mini

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research Agent là một trợ lý ảo chuyên tìm kiếm tin tức, trích xuất bài đăng từ Twitter, tổng hợp bài viết từ URL và đặc biệt có khả năng **đánh giá (triage) một nhận định (claim)** trước khi thực sự tìm kiếm bằng chứng. Agent có khả năng theo dõi ngữ cảnh hội thoại, chủ động hỏi lại khi thiếu thông tin và xác nhận an toàn trước khi thực hiện side-effects (như gửi tin nhắn).

**Link dùng thử (truy cập được trong showdown):**

Chạy local bằng lệnh `streamlit run app.py` và truy cập `http://localhost:8501`.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| `clarify` | Hỏi lại người dùng khi thiếu thông tin hoặc cần xác nhận yes/no | Không |
| `lookup` | Tra cứu thông tin, tin tức trên internet theo thời gian | Không |
| `social_search` | Tìm trên mạng xã hội Twitter theo từ khóa | Không |
| `timeline` | Lấy các bài đăng gần đây của một tài khoản Twitter | Không |
| `fetch` | Lấy nội dung text từ một địa chỉ URL cụ thể | Không |
| `format` | Trình bày dữ liệu đã có thành văn bản (markdown) | Không |
| `send` | Gửi một đoạn văn bản đi (vd: Telegram) | Không |
| `claim_check` | Đánh giá sơ bộ một nhận định (claim) thuộc chủ đề gì và mức độ khẩn cấp ra sao trước khi fact-check | **CÓ** |

## A3. Câu hỏi mẫu để thử

1. Đánh giá claim này giúp mình: Chơi game nhiều giúp tăng IQ.
2. Claim này đang viral, check gấp: OpenAI vừa phát hành GPT-5 tối qua.
3. Tin tức về AI hôm nay có gì?
4. Tóm tắt bài viết này giúp mình: https://openai.com/news
5. Gửi bản tóm tắt vừa rồi lên Telegram cho nhóm.

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| Đánh giá Claim khẩn cấp | `claim_check(domain="current_events", urgency="high")` | Agent phân loại chính xác các nhận định đang hot trên mạng để ưu tiên fact-check. | `runs/v3_B_group_openai...json` |
| Bổ sung thông tin URL | `clarify(response_type="text")` | Ở v0, agent tự nghĩ ra URL để tìm kiếm. Từ v1+, agent biết cách hỏi lại nếu user nói "bài viết này" nhưng quên paste link. | `runs/v3_B_base_openai...json` |
| Chuyển đổi công cụ (Switch tool) | `lookup` (chỉ gọi 1 tool) | Ở các version cũ, model hay tham lam gọi cả `social_search` và `lookup` cùng lúc khi user đổi ý. V3 đã sửa dứt điểm lỗi gọi thừa tool. | `runs/v3_B_group_openai...json` |

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version evidence

Dữ liệu được trích xuất từ `artifacts/version_log.csv` và `runs/*.json`:

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | baseline | Initial baseline run before prompt/tool optimization | `case_accuracy` | 0.00 | 0.70 | `v0_B_base_openai...json` |
| v1 | Thêm rules trong system_prompt và tools.yaml | Clearer routing boundaries and confirmation rules should make the agent ask clarify instead of guessing | `case_accuracy` | 0.70 | 0.90 | `v1_B_base_openai...json` |
| v2 | Tinh chỉnh prompt | The updated prompt should better ask for missing handle/URL and confirm before sending | `case_accuracy` | 0.90 | 0.90 | `v2_B_base_openai...json` |
| v3 | Siết chặt rule multi-turn | The updated prompt should resolve remaining ambiguous routing and correction cases | `case_accuracy` | 0.90 | 1.00 | `v3_B_base_openai...json` |

## B2. Failure analysis

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R08 (v0) | `out_of_scope` | `social_search` (ảo) | Hỏi bài toán nhưng prompt ép model phải gọi tool nghiên cứu | Thêm rule "OUT OF SCOPE" từ chối các câu không liên quan |
| R11 (v0) | `missing_info` | `lookup` / `fetch` | Nói "bài viết này" không link nhưng model tự đi search web | Thêm quy định cấm suy đoán URL, bắt buộc gọi `clarify` |
| R12 (v1) | `wrong_boundary` | `send` | Model gọi thẳng send mà không xin phép user | Bắt buộc phải gọi `clarify(yes_no)` trước các hành động gửi |
| M06 (v2) | `unnecessary_tool` | `social_search` + `lookup` | Khi user bảo "Bỏ Twitter", model vẫn gọi cả 2 tool | Thêm instruction nhấn mạnh "chỉ gọi 1 tool mỗi turn trừ khi yêu cầu song song" |

## B3. Team eval cases

Nhóm đã thiết kế 10 cases trong `data/eval_group.json` tập trung vào tool `claim_check` và xử lý ngữ cảnh đa lượt:

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01_claim_check_scientific | Đánh giá claim khoa học | `claim_check(domain="scientific")` | PASS |
| G02_claim_check_current_events | Đánh giá claim thời sự, khẩn cấp | `claim_check(domain="current_events", urgency="high")` | PASS |
| G03_fetch_not_claim_check | Đọc URL thông thường, không nhầm với claim | `fetch` | PASS |
| G04_missing_claim | Hỏi claim nhưng không đưa nội dung | `clarify` | PASS |
| G05_action_send_confirmation | Xác nhận trước khi gửi message | `clarify(yes_no)` | PASS |
| G06_multiturn_claim_fill | Multi-turn bổ sung claim từ turn trước | `claim_check` | PASS |
| G07_multiturn_switch_fetch_to_claim_check| Chuyển hướng từ đọc URL sang đánh giá claim | `claim_check` | PASS |
| G08_multiturn_carry_news_timeframe | Giữ nguyên timeframe="day" khi chuyển chủ đề | `lookup` | PASS |
| G09_multiturn_meta_no_tool | Trả lời câu hỏi thông thường, không gọi tool thừa | No tool | PASS |
| G10_multiturn_send_after_confirmation | Gọi send thực sự SAU khi user đã confirm "Có" | `send(confirmed=true)` | PASS |

## B4. Live chat evidence

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
| 1. Kiểm tra claim y tế | v3 | `claim_check(domain="scientific", urgency="normal")` | `transcripts/v3_B_group...json` | Agent nhận diện đúng là claim khoa học, gọi tool triage thành công. |
| 2. Gửi tóm tắt | v3 | `clarify(response_type="yes_no")` | `transcripts/v3_B_group...json` | Agent chặn lại và hỏi xác nhận người dùng thay vì tự gửi. |

## B5. Tool capability evidence

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: tool mới đầu tiên | `tools/claim_check` | Triage (phân loại) chính xác claim vào các nhóm như scientific, current_events. | Model có thể nhầm lẫn giữa truy vấn web thông thường và claim nếu câu nói không rõ ràng. Cần prompt định hướng kĩ. |

## B6. Reflection

- **Which fixes belonged in `system_prompt.md`?**
  Hầu hết các sửa đổi liên quan đến giới hạn an toàn (Boundary), xử lý khi thiếu thông tin (Missing info), và cách hành xử trong hội thoại đa lượt (Multi-turn switch) đều được giải quyết rất mượt mà thông qua `system_prompt.md`.
- **Which fixes belonged in `tools.yaml`?**
  Sử dụng thuộc tính `enum` cho các tham số như `domain`, `urgency`, `response_type` trong `tools.yaml` giúp ép model trả về tham số chuẩn xác 100%, thay vì phải dùng prompt hướng dẫn dông dài.
- **Which failure needed manual review instead of automatic grading?**
  Lỗi `extra_tool_call` (gọi thừa tool). Trình chấm tự động chỉ kiểm tra xem tool kì vọng có được gọi không, nhưng nếu model gọi tool kì vọng + 1 tool dư thừa thì chỉ có xem kĩ file JSON run mới phát hiện được.
- **What would you improve next?**
  Sau khi tool `claim_check` triage thành công, bước tiếp theo có thể nối thẳng luồng sang một tool `fact_check` để tự động query search và đối chiếu bằng chứng.

