# Monitoring & Observability (Future Plan)

Tài liệu này xác định các tiêu chuẩn giám sát cho AetherTutor khi vận hành ở quy mô lớn.

---

## 1. Metrics Collection

- **Infrastructure:** Prometheus + Node Exporter.
- **Application:** FastAPI (Prometheus Middleware).
- **AI API Performance:** latency, token usage, error rates.

## 2. Distributed Tracing

- **OpenTelemetry:** Theo dõi yêu cầu của người học xuyên suốt các Agent (Researcher -> Visualizer -> Tutor).

## 3. Logs Management

- **ELK Stack (Elasticsearch, Logstash, Kibana)** hoặc **Loki** cho trung tâm logs.

## 4. Alerting

- **Grafana Dashboards:** Trực quan hóa dữ liệu.
- **AlertManager:** Cảnh báo qua Slack/Email khi xảy ra lỗi hệ thống hoặc AI API quá tải.

---
> [!NOTE]
> Trong giai đoạn MVP, chúng tôi sử dụng logs đơn giản và Sentry để theo dõi lỗi ngoại lệ.
