import requests
import json
from django.conf import settings

class AlzajilClient:
    """
    عميل للتفاعل مع واجهة برمجة تطبيقات الزاجل (Alzajil Utility Payment Service).
    بناءً على وثائق 'alzajil (Utility Payment Service) v1.12'.
    """

    def __init__(self):
        # الإعدادات الأساسية والروابط
        self.payment_url = getattr(settings, 'ALZAJIL_PAYMENT_URL', 'https://alzajilonline.com:8444/api/tp/v1')
        self.report_url = getattr(settings, 'ALZAJIL_REPORT_URL', 'https://alzajilonline.com:8444/api/tp/v1')
        
        self.username = getattr(settings, 'ALZAJIL_USERNAME', '')
        self.security_token = getattr(settings, 'ALZAJIL_TOKEN', '')
        self.agent_user_id = getattr(settings, 'ALZAJIL_AGENT_USER_ID', '')
        
        # إعدادات التقارير
        self.report_username = getattr(settings, 'ALZAJIL_REPORT_USERNAME', '')
        self.report_password = getattr(settings, 'ALZAJIL_REPORT_PASSWORD', '')

    def _get_credentials(self, use_report=False):
        """
        إرجاع بيانات الاعتماد المناسبة بناءً على نوع الطلب.
        """
        if use_report:
            return self.report_username, self.report_password
        return self.agent_user_id, self.security_token

    def _send_request(self, params, method='GET', body=None, use_report=False):
        """
        دالة مساعدة لإرسال الطلبات إلى API.
        """
        # تحديد الرابط المناسب
        url = self.report_url if use_report else self.payment_url

        usr, tkn = self._get_credentials(use_report=use_report)

        # تجهيز الجسم (Body) إذا لم يكن موجوداً
        if body is None:
            body = {}
        
        # تحويل كافة مفاتيح الجسم إلى Lowercase لضمان التوافق مع توجيهات المستخدم
        # وكتحسين إضافي: تحويل جميع القيم إلى نصوص (Strings) مع مراعاة الأعداد الصحيحة
        final_body = {}
        for k, v in body.items():
            val = v
            if isinstance(v, float) and v.is_integer():
                val = int(v)
            final_body[k.lower()] = str(val)
        
        # إضافة المعاملات المشتركة بحروف صغيرة
        if usr:
            if method.upper() == 'POST':
                if 'usr' not in final_body: final_body['usr'] = usr
            else:
                if 'usr' not in params: params['usr'] = usr
        if tkn:
            if method.upper() == 'POST':
                if 'tkn' not in final_body: final_body['tkn'] = tkn
            else:
                if 'tkn' not in params: params['tkn'] = tkn

        try:
            if method.upper() == 'POST':
                response = requests.post(url, json=final_body, params=params, verify=False, timeout=30)
            else:
                response = requests.get(url, params=params, verify=False, timeout=30)
            
            # محاولة قراءة الاستجابة حتى لو كان الـ status code غير ناجح
            try:
                response_json = response.json()
                # Alzajil servers might return keys in varying cases.
                # Normalize typical keys to uppercase for consistency with Flutter UI.
                if isinstance(response_json, dict):
                    normalized = {}
                    for k, v in response_json.items():
                        key_lower = k.lower()
                        # List of typical keys to normalize to Uppercase
                        if key_lower in ['rc', 'msg', 'sd', 'bal', 'mt', 'loan', 'bill', 'ref', 'credit', 'bill_balance',
                                         'adamt', 'offer_id', 'offer_name', 'effdate', 'expdate', 'packages', 'list', 'name']:
                            normalized[key_lower.upper()] = v
                        else:
                            normalized[k] = v
                    return normalized
                return response_json
            except Exception as e:
                print(f"DEBUG: JSON Process Error: {e}")
                
                # Mask Token for display
                debug_body = final_body.copy()
                if 'tkn' in debug_body: debug_body['tkn'] = '***'
                
                # Use json.dumps to show valid JSON (double quotes) to the user
                debug_json_str = json.dumps(debug_body, ensure_ascii=False)

                return {
                    'RC': response.status_code,
                    'MSG': f'استجابة غير معالجة. الرابط: {url} | البيانات: {debug_json_str} | الخطأ: {response.text[:100]}'
                }
        except requests.exceptions.RequestException as e:
            # معالجة أخطاء الاتصال
            return {
                'RC': -100, # استخدام -100 كرمز خطأ عام للخدمة
                'MSG': f'خطأ في الاتصال: {str(e)}'
            }
        except json.JSONDecodeError:
             return {
                'RC': -1,
                'MSG': 'استجابة JSON غير صالحة من المزود'
            }

    def send_payment(self, data):
        """
        AC: 7100 (سداد)، 7200 (عروض)، 7600 (جملة)، 7700 (ترفيه)
        """
        # استخدام المفاتيح كما هي (Uppercase) لضمان التوافق
        return self._send_request(params={}, method='POST', body=data, use_report=False)

    def query_subscriber_balance(self, service_code, subscriber_no, action_code=4001):
        """
        AC: 4001 (الاستعلام عن رصيد المشترك)، قد يستخدم 4007 لبعض المزودين.
        """
        params = {'AC': action_code, 'SC': service_code, 'SNO': subscriber_no}
        # الاستعلام يستخدم GET وحساب التقارير
        return self._send_request(params=params, method='GET', use_report=True)

    def manage_offers(self, action_code, service_code, subscriber_no, offer_id=None):
        """
        AC: 4002-4007 (إدارة العروض)
        """
        params = {'AC': action_code, 'SC': service_code, 'SNO': subscriber_no}
        if offer_id:
            params['SAC'] = offer_id
        return self._send_request(params=params, method='GET', use_report=True)

    def query_agent_balance(self):
        """
        AC: 7400 (الاستعلام عن رصيد الوكيل)
        """
        return self._send_request(params={'AC': 7400}, method='GET', use_report=False)

    def check_transaction_status(self, trans_ref):
        """
        AC: 1003 (التحقق من حالة المعاملة)
        """
        return self._send_request(params={'AC': 1003, 'REF': trans_ref}, method='GET', use_report=False)
