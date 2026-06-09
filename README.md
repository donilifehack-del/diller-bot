# 🛒 Diller Boshqaruv Boti

Dillerlar uchun to'liq boshqaruv tizimi: dokonlar, tovarlar, buyurtmalar, qarzdorlar va tarix.

---

## 📁 Fayl tuzilmasi

```
diller_bot/
├── bot.py              ← Asosiy fayl (ishga tushirish)
├── config.py           ← Bot token
├── database.py         ← SQLite ma'lumotlar bazasi
├── requirements.txt    ← Kerakli kutubxonalar
└── handlers/
    ├── __init__.py
    ├── start_handler.py    ← Bosh menyu
    ├── shops_handler.py    ← Dokonlar
    ├── products_handler.py ← Tovarlar
    ├── orders_handler.py   ← Buyurtmalar
    ├── debtors_handler.py  ← Qarzdorlar
    └── history_handler.py  ← Tarix
```

---

## ⚙️ O'rnatish

### 1. Python 3.10+ o'rnating
https://www.python.org/downloads/

### 2. Bot tokenini oling
- Telegramda @BotFather ga yozing
- `/newbot` buyrug'ini bering
- Token nusxalab oling

### 3. `config.py` faylini o'zgartiring
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
# bu yerga o'z tokeningizni qo'ying
```

### 4. VS Code terminalida:
```bash
# Papkaga o'ting
cd diller_bot

# Virtual muhit yarating (ixtiyoriy lekin tavsiya etiladi)
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

# Kutubxonalarni o'rnating
pip install -r requirements.txt

# Botni ishga tushiring
python bot.py
```

---

## 🧩 Funksiyalar

| Bo'lim | Nima qiladi |
|--------|-------------|
| 🏪 Dokonlar | Dokon qo'shish, ko'rish, o'chirish |
| 📦 Tovarlar | Tovar qo'shish, narx/son o'zgartirish |
| 🛒 Buyurtma | Dokon + tovar tanlash, to'lov/qarz kiritish |
| 💸 Qarzdorlar | Faqat qarzli dokonlar, to'lov qabul qilish |
| 📊 Tarix | Kunlik hisobot, sana bo'yicha filtrlash |

---

## 📌 Eslatmalar

- Ma'lumotlar `diller.db` SQLite faylida saqlanadi
- Buyurtma berilganda tovar soni avtomatik kamayadi
- To'lov qabul qilganda eng eski qarzdan boshlab ayiriladi
- Tarixda so'nggi 30 kun ko'rinadi
