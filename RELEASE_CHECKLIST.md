# Release Checklist: 1C Processor Generator PRO

Фінальна перевірка перед запуском продажів.
Виконувати послідовно - кожен крок залежить від попереднього.

---

## 1. Пакет (pip install)

Перше - переконатись що пакет взагалі працює.

### 1.1 Встановлення в чистому середовищі
```bash
python -m venv test_clean
test_clean/Scripts/pip install 1c-processor-generator
```
- [ ] Встановлюється без помилок
- [ ] Всі залежності підтягуються (cairosvg, cryptography, lxml...)
- [ ] Версія актуальна: `python -m 1c_processor_generator --version`

### 1.2 Захист на місці
```bash
# Перевірити що .pyd файли є
test_clean/Scripts/python -c "
import glob
pyd = glob.glob('test_clean/Lib/site-packages/1c_processor_generator/**/*.pyd', recursive=True)
print(f'Found {len(pyd)} .pyd files')
for f in pyd: print(f'  {f.split(\"1c_processor_generator\")[-1]}')
"
```
- [ ] `_protected.pyd` присутній
- [ ] `pro/*.pyd` присутні (12 файлів)
- [ ] Немає `_protected.py` source
- [ ] Немає `pro/*.py` source (крім `__init__.py`)

### 1.3 Базова функціональність (FREE)
```bash
# XML генерація - має працювати без ліцензії
python -m 1c_processor_generator yaml \
  --config examples/yaml/business_card_demo/config.yaml \
  --handlers-file examples/yaml/business_card_demo/handlers.bsl \
  --output /tmp/test_free
```
- [ ] XML генерується успішно
- [ ] Watermark присутній (FREE версія)

---

## 2. Ліцензійний сервер

Тепер перевіряємо що сервер відповідає.

### 2.1 Доступність
```bash
curl -I https://license.itdeo.tech/api/health
```
- [ ] Сервер відповідає (200 OK)
- [ ] HTTPS працює
- [ ] Час відповіді < 2 сек

### 2.2 Endpoint: Активація
```bash
curl -X POST https://license.itdeo.tech/api/activate \
  -H "Content-Type: application/json" \
  -d '{"license_key": "PRO-TEST-VALID-KEY", "machine_id": "test123", "product": "1c-processor-generator"}'
```
- [ ] Валідний ключ → success: true
- [ ] Невалідний ключ → зрозуміла помилка
- [ ] Expired ключ → зрозуміла помилка
- [ ] Перевищено ліміт машин → зрозуміла помилка

### 2.3 Endpoint: Верифікація
```bash
curl -X POST https://license.itdeo.tech/api/verify \
  -H "Content-Type: application/json" \
  -d '{"license_key": "PRO-TEST-VALID-KEY", "machine_id": "test123"}'
```
- [ ] Активована ліцензія → success: true
- [ ] Неактивована → помилка

### 2.4 Endpoint: Trial
```bash
curl -X POST https://license.itdeo.tech/api/trial \
  -H "Content-Type: application/json" \
  -d '{"machine_id": "test123", "email": "test@example.com"}'
```
- [ ] Новий machine_id → видає trial ключ
- [ ] Повторний запит → "trial already used"

### 2.5 Edge cases сервера
- [ ] Сервер недоступний 5 хв → grace period в клієнті працює?
- [ ] Rate limiting: 100 запитів/хв → блокує?
- [ ] Логування: всі активації записуються?

---

## 3. Активація з клієнта

Тепер перевіряємо що пакет + сервер працюють разом.

### 3.1 Команда activate
```bash
python -m 1c_processor_generator activate PRO-TEST-VALID-KEY
```
- [ ] Успішна активація → "Ліцензію активовано"
- [ ] Токен зберігся локально
- [ ] Невалідний ключ → зрозуміла помилка

### 3.2 Команда license-status
```bash
python -m 1c_processor_generator license-status
```
- [ ] Показує тип ліцензії
- [ ] Показує дату закінчення
- [ ] Показує machine_id (--show-machine-id)

### 3.3 Команда trial
```bash
python -m 1c_processor_generator trial
```
- [ ] Видає trial ліцензію
- [ ] 7 днів терміну

### 3.4 Grace period
- [ ] Вимкнути інтернет
- [ ] Перевірити що PRO функції працюють ще 7 днів
- [ ] Після 7 днів → блокується

---

## 4. PRO функції

Перевіряємо що ліцензія дійсно розблоковує PRO.

### 4.1 EPF компіляція (з ліцензією)
```bash
python -m 1c_processor_generator yaml \
  --config examples/yaml/business_card_demo/config.yaml \
  --handlers-file examples/yaml/business_card_demo/handlers.bsl \
  --output /tmp/test_pro \
  --output-format epf
```
- [ ] EPF файл створюється
- [ ] Немає watermark

### 4.2 EPF компіляція (без ліцензії)
```bash
# Очистити токен
python -m 1c_processor_generator cache-clear

# Спробувати EPF
python -m 1c_processor_generator yaml ... --output-format epf
```
- [ ] Повідомлення про необхідність ліцензії
- [ ] Посилання на покупку
- [ ] XML все ще працює (fallback)

### 4.3 Watermark
- [ ] FREE: watermark в BSL коді присутній
- [ ] PRO: watermark відсутній
- [ ] Trial: watermark відсутній

---

## 5. Лендінг

Перевіряємо сайт та інформацію.

### 5.1 Сторінки
- [ ] Головна завантажується
- [ ] Pricing коректний (Quarter/Year/Lifetime)
- [ ] Опис FREE vs PRO чіткий
- [ ] Документація доступна
- [ ] Контакти підтримки видні

### 5.2 SEO/Meta
- [ ] Title коректний
- [ ] Description заповнений
- [ ] OG tags для соцмереж

### 5.3 Mobile
- [ ] Сайт адаптивний
- [ ] Кнопки клікабельні

---

## 6. Оплата

Перевіряємо платіжну систему.

### 6.1 Checkout flow
- [ ] Кнопка "Купити" веде на checkout
- [ ] Всі плани доступні для вибору
- [ ] Ціни коректні

### 6.2 Тестова покупка
- [ ] Оплата проходить (тестова картка)
- [ ] Webhook спрацьовує
- [ ] Ліцензійний ключ генерується в базі

### 6.3 Після оплати
- [ ] Redirect на success page
- [ ] Success page містить ключ або інструкцію
- [ ] Email відправляється

---

## 7. Email

Перевіряємо доставку листів.

### 7.1 Доставка
- [ ] Email доходить (не в спамі)
- [ ] Перевірити Gmail, Outlook, корпоративну пошту

### 7.2 Зміст email
- [ ] Ліцензійний ключ присутній
- [ ] Інструкція з активації
- [ ] Контакти підтримки
- [ ] Посилання на документацію

### 7.3 Технічне
- [ ] Reply-to налаштований
- [ ] Plain text версія є
- [ ] SPF/DKIM налаштовані (для доставки)

---

## 8. End-to-End (фінальний тест)

Повний шлях клієнта від початку до кінця.

```
1. Відкрити сайт інкогніто
2. Переглянути pricing
3. Натиснути "Купити Year"
4. Оплатити тестовою карткою
5. Отримати email з ключем
6. pip install 1c-processor-generator
7. python -m 1c_processor_generator activate KEY
8. Згенерувати EPF
9. Відкрити EPF в 1С
```

- [ ] Весь шлях проходить без проблем
- [ ] Час від оплати до активації < 5 хвилин
- [ ] EPF працює в 1С

---

## 9. Що можеш забути

### Ліцензії
- [ ] Як клієнт перенесе на інший комп? (є deactivate?)
- [ ] Що якщо переставив Windows? (machine_id зміниться)
- [ ] Як продовжити ліцензію? (новий ключ чи extend existing?)
- [ ] Що якщо купив двічі помилково?

### Платежі
- [ ] Refund policy визначена?
- [ ] Що якщо платіж failed? (клієнт бачить помилку?)
- [ ] Логування транзакцій?

### Підтримка
- [ ] Email підтримки моніториться?
- [ ] Хто відповідає у вихідні?
- [ ] FAQ готовий для типових питань?

### Версії
- [ ] Стара версія пакету + новий сервер API = сумісно?
- [ ] Breaking changes в API версіоновані?

---

## 10. Юридичне

- [ ] EULA опублікована на сайті
- [ ] Privacy Policy опублікована
- [ ] Checkbox "Погоджуюсь" при покупці
- [ ] Політика повернення коштів описана

---

## 11. Після запуску (перший тиждень)

- [ ] Моніторити uptime сервера
- [ ] Перевіряти email підтримки щодня
- [ ] Слідкувати за відгуками
- [ ] Швидко фіксити критичні баги
- [ ] Збирати feedback

---

## Статус готовності

| # | Категорія | Статус |
|---|-----------|--------|
| 1 | Пакет (pip install) | ⬜ |
| 2 | Ліцензійний сервер | ⬜ |
| 3 | Активація з клієнта | ⬜ |
| 4 | PRO функції | ⬜ |
| 5 | Лендінг | ⬜ |
| 6 | Оплата | ⬜ |
| 7 | Email | ⬜ |
| 8 | End-to-End тест | ⬜ |
| 9 | Edge cases | ⬜ |
| 10 | Юридичне | ⬜ |

**Всі ⬜ → ✅ = GO!**

---

*Last updated: 2024-12-13*
