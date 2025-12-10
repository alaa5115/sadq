from flask import Flask, request, jsonify, send_file
from flask_cors import CORS 
from werkzeug.exceptions import RequestEntityTooLarge 
import io
import os
import datetime
import base64
from PIL import Image, ImageChops # ImageChops ضرورية لـ ELA
from PIL.ExifTags import TAGS
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from flask import Flask, request, jsonify, send_file, session # <-- إضافة session
from flask_cors import CORS 
# ... (باقي الاستيرادات)

app = Flask(__name__)
# ⚠️ **هام:** يجب تعيين مفتاح سري لجلسات Flask (استبدل 'your_secret_key_here' بشيء فريد وآمن)
app.secret_key = 'your_strong_and_unique_secret_key_here_for_security' 
# ... (باقي إعدادات Flask)

# =========================================================
# 1. التحصين: استيراد ملفات التحليل مع دوال احتياطية (Fallbacks)
# =========================================================

# استيراد أدوات التحليل AI
try:
    from ai_forensics import analyze_with_ai, build_forensics_model
    
    print("⏳ جاري بناء نموذج الذكاء الاصطناعي...")
    # بناء النموذج عالمياً عند بدء التشغيل
    GLOBAL_AI_MODEL = build_forensics_model()
    # إذا كان لديك ملف أوزان، قم بإلغاء التعليق عن السطر التالي:
    # GLOBAL_AI_MODEL.load_weights('model_weights.h5')
    print("✅ تم إعداد النموذج (استخدام أوزان عشوائية/أوزان محملة).")
    
except ImportError as e:
    print(f"WARNING: فشل استيراد وحدة الذكاء الاصطناعي: {e}")
    # دالة احتياطية تقبل 3 وسائط وترجع 4 قيم
    def analyze_with_ai(image_stream, global_model, ela_weight, prnu_score):
        return 0.0, f"❌ خطأ: فشل تحميل نموذج الذكاء الاصطناعي. {str(e)}", None, 0.0

# استيراد أدوات التحليل PRNU
try:
    from prnu_analysis import extract_noise_pattern
except ImportError as e:
    print(f"WARNING: فشل استيراد وحدة PRNU: {e}")
    # دالة احتياطية ترجع 3 قيم
    def extract_noise_pattern(image_stream):
        return f"❌ خطأ: فشل تحميل وحدة PRNU. {str(e)}", 0.0, None


# =========================================================
# 2. إعداد ReportLab ودعم اللغة العربية (Tajawal)
# =========================================================

try:
    # يجب أن يكون ملف الخط 'Tajawal-Bold.ttf' موجوداً في نفس المجلد
    pdfmetrics.registerFont(TTFont('Tajawal', 'Tajawal-Bold.ttf'))
    ARABIC_FONT = 'Tajawal'
except Exception as e:
    print(f"WARNING: فشل تحميل خط Tajawal: {e}. سيتم استخدام الخط الافتراضي.")
    ARABIC_FONT = 'Helvetica'

@app.route('/api/analyze', methods=['POST'])
def analyze_endpoint():
    """نقطة نهاية لتحليل الصورة."""

    # ----------------------------------------------
    # 🌟 منطق التحقق من المحاولات المجانية 🌟
    # ----------------------------------------------
    # الحد الأقصى للمحاولات المجانية
    FREE_TRIES_LIMIT = 1 
    
    # التحقق من عدد المحاولات المتبقية في الجلسة (Session)
    if 'tries_left' not in session:
        session['tries_left'] = FREE_TRIES_LIMIT
    
    tries_left = session['tries_left']

    if tries_left <= 0:
        # إذا انتهت المحاولات
        error_message = "⚠️ انتهت محاولتك المجانية. الرجاء الترقية/الاشتراك للمزيد من التحليلات."
        print("❌ DENIED: Free trial limit reached.")
        # نعيد أيضًا عدد المحاولات المتبقية للمتصفح ليحدث الواجهة
        return jsonify({"error": error_message, "tries_left": tries_left}), 402 # 402: Payment Required

    # خصم محاولة واحدة
    session['tries_left'] -= 1
    # ----------------------------------------------
    
    # ... (باقي التحقق من الملفات والتحليل كما هو)
    
    # ... (في نهاية التحليل الناجح)
    # **تعديل:** أضف عدد المحاولات المتبقية في الاستجابة الناجحة
    results = {
        # ... (نتائج التحليل الأخرى)
        "tries_left": session['tries_left'] # إرجاع عدد المحاولات المتبقية
    }
    
    return jsonify(results) # تحويله إلى JSON
# ... (باقي الكود)
# =========================================================
# 3. دوال تحليل الصور المساعدة (ELA)
# =========================================================

def perform_ela_analysis(image_stream, quality=90):
    """
    إجراء تحليل مستوى خطأ الانضغاط (ELA) على الصورة.
    """
    ela_base64_image = None
    ela_trust_score = 0.0
    ela_verdict = "❌ فشل تحليل ELA."
    
    try:
        # 1. قراءة الصورة الأصلية
        image_stream.seek(0)
        original_img = Image.open(image_stream).convert('RGB')
        
        # 2. حفظ الصورة بجودة منخفضة (90)
        temp_buffer = io.BytesIO()
        original_img.save(temp_buffer, format='JPEG', quality=quality)
        temp_buffer.seek(0)
        
        # 3. إعادة قراءة الصورة المضغوطة
        compressed_img = Image.open(temp_buffer).convert('RGB')
        
        # 4. حساب الاختلاف (ELA)
        ela_img = ImageChops.difference(original_img, compressed_img)
        
        # 5. تعزيز الصورة لجعل المناطق المتلاعب بها مرئية
        # تحويل الصورة إلى مصفوفة NumPy
        np_ela = np.array(ela_img, dtype=np.float32)
        # تعزيز التباين (توسيع النطاق)
        max_diff = np_ela.max()
        if max_diff > 0:
             np_ela = (np_ela / max_diff) * 255.0
        
        # 6. حساب درجة الثقة (محاكاة)
        # مؤشر متوسط فرق البكسل (متوسط الضوضاء)
        mean_diff = np.mean(np_ela) 
        
        # القيم المرجعية (مُحاكاة): الأصيل له قيمة متوسطة منخفضة
        if mean_diff < 15: # أصيل
            ela_trust_score = 95.0 - (mean_diff / 15.0) * 15.0
            ela_verdict = f"✅ أصالة عالية. متوسط تباين ELA منخفض ({mean_diff:.2f})."
        elif mean_diff > 35: # مزور
            ela_trust_score = 10.0 + (35.0 / mean_diff) * 20.0
            ela_verdict = f"⚠️ تباين ELA مرتفع جداً ({mean_diff:.2f}). يشير إلى تعديل كبير."
        else: # حذر
            ela_trust_score = 80.0 - ((mean_diff - 15) / 20.0) * 40.0
            ela_verdict = f"🟡 تباين ELA متوسط ({mean_diff:.2f}). يُنصح بمزيد من التدقيق."

        
        # 7. تحويل صورة ELA إلى Base64
        ela_img_scaled = Image.fromarray(np_ela.astype(np.uint8))
        buffer = io.BytesIO()
        ela_img_scaled.save(buffer, format="PNG")
        ela_base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # الإصلاح: التأكد من أن جميع القيم الرقمية هي float
        return ela_verdict, float(ela_trust_score), ela_base64_image
        
    except Exception as e:
        print(f"Error in ELA analysis: {e}")
        return f"❌ فشل حرج في تحليل ELA: {str(e)}", 0.0, None


# =========================================================
# 4. دالة التحليل الرئيسية التي تجمع الكل
# =========================================================

def run_full_analysis(image_stream):
    """تنسيق وتشغيل جميع التحليلات."""
    
    # 1. تحليل ELA
    ela_message, ela_score, ela_base64_image = perform_ela_analysis(image_stream)
    
    # 2. تحليل PRNU (يجب إعادة تعيين مؤشر الدفق)
    image_stream.seek(0) 
    prnu_message, prnu_score, prnu_base64_image = extract_noise_pattern(image_stream) 
    
    # 3. تحليل الذكاء الاصطناعي (يجب إعادة تعيين مؤشر الدفق)
    image_stream.seek(0)
    # ملاحظة: نمرر درجة ELA و PRNU لمساعدة نموذج AI في دمج القرار
    final_combined_score, ai_message, gradcam_base64_image, ai_score_raw = analyze_with_ai(
        image_stream, GLOBAL_AI_MODEL, ela_score, prnu_score
    )
    
    # 4. تجميع النتائج
    results = {
        'ela_message': ela_message,
        'ela_score': float(ela_score),
        'ela_base64_image': ela_base64_image,
        
        'prnu_message': prnu_message,
        'prnu_score': float(prnu_score),
        'prnu_base64_image': prnu_base64_image,
        
        'ai_message': ai_message,
        'ai_score_raw': float(ai_score_raw),
        'gradcam_base64_image': gradcam_base64_image,
        
        # القرار النهائي المدمج (من دالة AI)
        'final_combined_score': float(final_combined_score)
    }
    
    return results

# =========================================================
# 5. دوال Flask والـ API
# =========================================================

app = Flask(__name__)
# تحديد حجم الملف الأقصى بـ 10 ميجابايت (للسلامة)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 
CORS(app) 

# ... (باقي دوال generate_pdf_report و routes) ...
def generate_pdf_report(data):
    """توليد تقرير PDF مفصل من بيانات التحليل."""
    
    # تنسيق التاريخ والوقت
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont(ARABIC_FONT, 24)
    p.drawString(400, 750, "تقرير تحليل أصالة الصورة (منصة صِدق)")
    
    p.setFont(ARABIC_FONT, 14)
    p.drawString(72, 720, f"تاريخ التقرير: {current_datetime}")
    p.drawString(72, 700, f"القرار النهائي المدمج: {data.get('final_combined_score', 0.0):.2f}%")
    
    # إضافة الأقسام
    y_position = 650
    p.setFont(ARABIC_FONT, 16)
    p.drawString(72, y_position, "1. ملخص نتائج التحليل الرقمي:")
    
    y_position -= 30
    p.setFont(ARABIC_FONT, 12)
    p.drawString(72, y_position, f"درجة ELA: {data.get('ela_score', 0.0):.2f}% - الرسالة: {data.get('ela_message', 'N/A')}")
    y_position -= 20
    p.drawString(72, y_position, f"درجة PRNU: {data.get('prnu_score', 0.0):.2f}% - الرسالة: {data.get('prnu_message', 'N/A')}")
    y_position -= 20
    p.drawString(72, y_position, f"درجة الذكاء الاصطناعي: {data.get('ai_score_raw', 0.0):.2f}% - الرسالة: {data.get('ai_message', 'N/A')}")
    
    # إضافة صورة ELA
    y_position -= 40
    p.setFont(ARABIC_FONT, 14)
    p.drawString(72, y_position, "2. تحليل مستوى خطأ الانضغاط (ELA):")
    y_position -= 10
    
    try:
        if data.get('ela_base64_image'):
            img_data = base64.b64decode(data['ela_base64_image'])
            img = Image.open(io.BytesIO(img_data))
            # الحجم: 200x200
            p.drawInlineImage(img, 72, y_position - 200, width=200, height=200)
            y_position -= 210
    except Exception as e:
        p.drawString(72, y_position - 20, f"فشل عرض صورة ELA: {str(e)}")
        y_position -= 40
    
    # إضافة صورة PRNU
    p.setFont(ARABIC_FONT, 14)
    p.drawString(300, y_position, "3. تحليل نمط ضوضاء المستشعر (PRNU):")
    y_position -= 10
    
    try:
        if data.get('prnu_base64_image'):
            img_data = base64.b64decode(data['prnu_base64_image'])
            img = Image.open(io.BytesIO(img_data))
            p.drawInlineImage(img, 300, y_position - 200, width=200, height=200)
            y_position -= 210
    except Exception as e:
        p.drawString(300, y_position - 20, f"فشل عرض صورة PRNU: {str(e)}")
        y_position -= 40
        
    # إضافة خريطة Grad-CAM (في صفحة جديدة إذا لم يكن هناك مساحة)
    if y_position < 150:
        p.showPage()
        y_position = 750
    
    p.setFont(ARABIC_FONT, 14)
    p.drawString(72, y_position, "4. خريطة تركيز الذكاء الاصطناعي (Grad-CAM):")
    y_position -= 10
    
    try:
        if data.get('gradcam_base64_image'):
            img_data = base64.b64decode(data['gradcam_base64_image'])
            img = Image.open(io.BytesIO(img_data))
            # يمكن أن تكون الصورة أكبر حجماً
            p.drawInlineImage(img, 72, y_position - 250, width=400, height=250)
            y_position -= 260
        else:
            p.drawString(72, y_position - 20, "لم يتم توليد خريطة Grad-CAM.")
            y_position -= 40
    except Exception as e:
        p.drawString(72, y_position - 20, f"فشل عرض خريطة Grad-CAM: {str(e)}")
        y_position -= 40
        
    p.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
# في app_flask.py، داخل دالة analyze_endpoint
@app.route('/api/analyze', methods=['POST'])
def analyze_endpoint():
    """نقطة نهاية لتحليل الصورة."""

    # ----------------------------------------------
    # 🌟 منطق التحقق من المحاولات المجانية 🌟
    # ----------------------------------------------
    
    # 1. التحقق من حالة الاشتراك
    is_subscribed = session.get('is_subscribed', False)

    if not is_subscribed:
        # إذا لم يكن مشتركاً، طبق منطق المحاولات المجانية
        FREE_TRIES_LIMIT = 1 
        
        if 'tries_left' not in session:
            session['tries_left'] = FREE_TRIES_LIMIT
        
        tries_left = session['tries_left']

        if tries_left <= 0:
            error_message = "⚠️ انتهت محاولتك المجانية. الرجاء الترقية/الاشتراك للمزيد من التحليلات."
            print("❌ DENIED: Free trial limit reached.")
            return jsonify({"error": error_message, "tries_left": tries_left}), 402 # 402: Payment Required

        # خصم محاولة واحدة
        session['tries_left'] -= 1
        print(f"✅ Free try used. Tries left: {session['tries_left']}")
    
    else:
        # المشتركين لديهم محاولات غير محدودة
        session['tries_left'] = -1 # قيمة رمزية تدل على اللانهاية
        print("✅ SUBSCRIBER: Unlimited access granted.")
    # ----------------------------------------------
    
    # ... (بقية كود التحليل)
    
    # ... (في نهاية التحليل الناجح)
    results = {
        # ... (نتائج التحليل الأخرى)
        "tries_left": session['tries_left'] 
    }
    
    return jsonify(results)

@app.route('/api/download_report', methods=['POST'])
def download_report_endpoint():
    """نقطة نهاية تحميل التقرير."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided for report generation"}), 400
    try:
        pdf_bytes = generate_pdf_report(data)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"Sedq_Analysis_Report_{datetime.date.today()}.pdf"
        )
    except Exception as e:
        print(f"Error in PDF generation endpoint: {e}")
        return jsonify({"error": f"فشل توليد التقرير: {str(e)}"}), 500


@app.route('/')
def index():
    return send_file('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    if os.path.exists(filename):
        # التحصين ضد خطأ في MIME Type لبعض أنواع الملفات
        return send_file(filename)
    else:
        return "404 Not Found", 404

if __name__ == '__main__':
    # وضع الخادم على الوضع الافتراضي للـ Demo
    app.run(debug=True, host='127.0.0.1', port=5000)
    # ... (في نهاية ملف app_flask.py، بعد الدالة analyze_endpoint)

@app.route('/api/check_tries', methods=['GET'])
def check_tries_endpoint():
    """نقطة نهاية لمعرفة عدد المحاولات المتبقية عند تحميل الصفحة."""
    FREE_TRIES_LIMIT = 1 
    if 'tries_left' not in session:
        session['tries_left'] = FREE_TRIES_LIMIT
        
    return jsonify({"tries_left": session['tries_left']})

# في ملف app_flask.py، أضف الاستيراد وتهيئة Stripe
import stripe # <-- إضافة هذا السطر
# ⚠️ استبدل المفتاح التالي بمفتاحك السري الحقيقي من Stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") 


@app.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """تنشئ جلسة دفع مع Stripe وتحول المستخدم إليها."""
    try:
        data = request.json
        plan_id = data.get('plan_id') # ستكون 'monthly' أو 'yearly' من scripts.js

        # تحديد سعر المنتج بناءً على الخطة المختارة (يجب أن تتطابق مع أسعارك في Stripe)
        # مثال:
        if plan_id == 'monthly':
            price_id = 'price_XXX_monthly' # Price ID من لوحة تحكم Stripe
        elif plan_id == 'yearly':
            price_id = 'price_YYY_yearly' # Price ID من لوحة تحكم Stripe
        else:
            return jsonify({'error': 'Invalid plan selected'}), 400

        # إنشاء جلسة الدفع في Stripe
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                }
            ],
            mode='subscription', # أو 'payment' إذا كان دفع لمرة واحدة
            success_url=request.url_root + 'index.html?payment=success', # عنوان العودة عند النجاح
            cancel_url=request.url_root + 'payment.html?payment=cancelled', # عنوان العودة عند الإلغاء
        )
        
        # إرسال رابط Stripe إلى الواجهة الأمامية
        return jsonify({
            'session_id': session.id,
            'stripe_checkout_url': session.url
        })

    except Exception as e:
        print(f"Stripe Session Error: {e}")
        return jsonify(error=str(e)), 500


# ----------------------------------------------------------------
# نقطة نهاية الاستماع لحدث Stripe (Webhook) - ضرورية لتفعيل الاشتراك
# ----------------------------------------------------------------
@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('stripe-signature')
    event = None

    try:
        # التحقق من توقيع الحدث
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get("STRIPE_WEBHOOK_SECRET")
        )
    except ValueError as e:
        # توقيع غير صالح
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # توقيع غير صالح
        return 'Invalid signature', 400

    # معالجة حدث إتمام الدفع بنجاح
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # ⚠️ **الخطوة الحاسمة:** يجب عليك هنا ربط هذا الاشتراك
        # بمعرّف المستخدم الحقيقي في قاعدة بياناتك (إذا كنت تستخدم قاعدة بيانات)
        
        # بما أننا لا نستخدم قاعدة بيانات، سنكتفي بالتأكيد اللفظي:
        print(f"💰 PAYMENT SUCCESS: Session {session.id} completed. Subscription should be activated.")
        
    return jsonify({'status': 'success'}), 200
@app.route('/api/activate_subscription', methods=['POST'])
def activate_subscription_endpoint():
    """نقطة نهاية محاكاة تفعيل الاشتراك (للاستخدام المؤقت مع الجلسات)."""
    
    # 1. تحقق من بيانات الفورم (للتأكد من اختيار خطة)
    data = request.json
    selected_plan = data.get('plan')
    
    if not selected_plan:
        return jsonify({"error": "الرجاء اختيار باقة دفع صالحة"}), 400

    # 2. 🌟 تفعيل الاشتراك في الجلسة 🌟
    # هذا هو العنصر الأساسي الذي يمنح المستخدم وصولاً غير محدود.
    session['is_subscribed'] = True
    session['tries_left'] = -1 # قيمة رمزية لـ "غير محدود"
    
    # 3. إرجاع تأكيد بالنجاح
    return jsonify({
        "success": True, 
        "message": f"تم تفعيل اشتراكك بنجاح في خطة: {selected_plan}",
        "is_subscribed": session['is_subscribed']
    })


@app.route('/api/check_tries', methods=['GET'])
def check_tries_endpoint():
    """نقطة نهاية للتحقق الأولي من عدد المحاولات/حالة الاشتراك."""
    FREE_TRIES_LIMIT = 1 
    
    # التحقق أولاً من الاشتراك الدائم (المؤقت)
    if session.get('is_subscribed', False):
        return jsonify({"tries_left": -1, "is_subscribed": True})
        
    if 'tries_left' not in session:
        session['tries_left'] = FREE_TRIES_LIMIT
        
    return jsonify({"tries_left": session['tries_left'], "is_subscribed": False})

# ... (بقية الكود)

if __name__ == '__main__':
    # هذا الجزء يستخدم للتشغيل المحلي فقط.
    # Gunicorn يتجاهل هذا الجزء ويستخدم الأمر في Procfile
    app.run(debug=True, host='0.0.0.0')