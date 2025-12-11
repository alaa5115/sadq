import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from tensorflow.keras.optimizers import Adam 
import numpy as np
import os
import sys

# حجم الصورة الذي يتطلبه النموذج (مطابق لـ ai_forensics.py)
IMG_SIZE = 128
MODEL_PATH = 'forensics_model.h5'

# =========================================================
# 1. تعريف النموذج (يجب أن يطابق ما في ai_forensics.py)
# =========================================================

def build_forensics_model():
    """بناء نموذج شبكة عصبية تلافيفية (CNN) للكشف عن التلاعب."""
    
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(IMG_SIZE, IMG_SIZE, 3)),
        MaxPooling2D((2, 2)),
        
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        
        Conv2D(128, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        
        Flatten(),
        Dense(64, activation='relu'),
        Dense(1, activation='sigmoid') # لإخراج قيمة بين 0 و 1 (مزور/أصلي)
    ])
    
    model.compile(optimizer=Adam(learning_rate=0.0001), 
                  loss='binary_crossentropy', 
                  metrics=['accuracy'])
    
    return model

# =========================================================
# 2. توليد بيانات وهمية وتدريب سريع
# =========================================================

if __name__ == '__main__':
    print("بدء عملية توليد وتدريب النموذج الوهمي...")
    
    # ⚠️ تحقق من أن TensorFlow يعمل بشكل صحيح
    try:
        if tf.config.list_physical_devices('GPU'):
            print("TensorFlow يستخدم معالج الرسوميات (GPU).")
        else:
            print("TensorFlow يستخدم المعالج المركزي (CPU).")
    except Exception:
        print("تحذير: فشل التحقق من إعدادات TensorFlow.")
        
    # توليد بيانات وهمية بسيطة (100 صورة)
    # 100 صورة، بحجم 128x128، وثلاث قنوات لونية (RGB)
    X_mock = np.random.rand(100, IMG_SIZE, IMG_SIZE, 3).astype('float32')
    y_mock = np.random.randint(0, 2, 100) # تسميات وهمية: 0 أو 1

    # بناء النموذج
    model = build_forensics_model()

    # تدريب سريع جداً (epoch واحد فقط) لحفظ الأوزان
    # هذه الخطوة لا تهدف إلى تدريب النموذج فعلياً، بل لتوليد ملف الأوزان.
    print("تدريب سريع (1 Epoch) لتوليد ملف الأوزان...")
    try:
        model.fit(X_mock, y_mock, epochs=1, batch_size=32, verbose=0)
    except Exception as e:
        print(f"❌ فشل التدريب السريع. قد تكون لديك مشكلة في تثبيت NumPy/TensorFlow: {e}")
        sys.exit(1)

    # =========================================================
    # 3. حفظ النموذج (لتوليد الملف المفقود)
    # =========================================================
    try:
        model.save(MODEL_PATH)
        
        # التأكد من حفظ الملف
        if os.path.exists(MODEL_PATH):
            print(f"✅ نجاح: تم حفظ نموذج وهمي بنجاح باسم: {MODEL_PATH}")
            print("\nالآن يمكنك تشغيل خادم Flask بأمان.")
        else:
            print(f"❌ فشل: لم يتم العثور على الملف {MODEL_PATH} بعد عملية الحفظ.")
            
    except Exception as e:
        print(f"❌ فشل حفظ النموذج: {e}")