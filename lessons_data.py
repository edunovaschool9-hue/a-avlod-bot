"""
1 oylik dars testlari - A Avlod Academy
Har bir dars uchun 5 ta savol, har biri 5 bayt
"""

MONTHLY_LESSONS = [
    {
        "id": 1,
        "title": "Sun'iy intellekt do'stlarim",
        "week": 1,
        "description": "ChatGPT, Gemini va Claude haqida bilib olamiz",
        "tests": [
            {
                "question": "ChatGPT qaysi kompaniya tomonidan yaratilgan?",
                "options": ["Google", "OpenAI", "Apple", "Microsoft"],
                "correct": 1
            },
            {
                "question": "Gemini sun'iy intellektini kim yaratgan?",
                "options": ["Apple", "OpenAI", "Google", "Amazon"],
                "correct": 2
            },
            {
                "question": "Claude sun'iy intellektini qaysi kompaniya yaratgan?",
                "options": ["Meta", "Anthropic", "OpenAI", "Google"],
                "correct": 1
            },
            {
                "question": "Sun'iy intellekt nima qila oladi?",
                "options": [
                    "Faqat rasmlar chizadi",
                    "Savollarga javob beradi, she'r yozadi, masala yechadi",
                    "Faqat o'yin o'ynaydi",
                    "Hech narsa qila olmaydi"
                ],
                "correct": 1
            },
            {
                "question": "Murodjon birinchi marta qaysi sun'iy intellekt haqida eshitdi?",
                "options": ["Gemini", "Siri", "ChatGPT", "Claude"],
                "correct": 2
            }
        ]
    },
    {
        "id": 2,
        "title": "Kamera bilan tanishuv",
        "week": 1,
        "description": "Kamera oldida o'zimizni qulay his qilishni o'rganamiz",
        "tests": [
            {
                "question": "Kamera oldida gaplashishdan qo'rqmaslik uchun nima qilish kerak?",
                "options": [
                    "Umuman gapirmaslik",
                    "Ko'p mashq qilish",
                    "Kamerani yoqmaslik",
                    "Faqat yozib borish"
                ],
                "correct": 1
            },
            {
                "question": "AEIOU mashqi nima uchun kerak?",
                "options": [
                    "Rasm chizish uchun",
                    "Og'iz mushaklarini tayyorlash uchun",
                    "Uxlash uchun",
                    "O'yin o'ynash uchun"
                ],
                "correct": 1
            },
            {
                "question": "Murodjon birinchi marta nima qildi?",
                "options": [
                    "Video yukladi",
                    "Kamerani ochdi",
                    "Televizor ko'rdi",
                    "Uxlab qoldi"
                ],
                "correct": 1
            },
            {
                "question": "Yaxshi ovoz uchun avval nima qilish kerak?",
                "options": [
                    "Baland qichqirish",
                    "Burndan chuqur nafas olish",
                    "Suv ichish",
                    "Yugurish"
                ],
                "correct": 1
            },
            {
                "question": "Bloger bo'lish uchun eng muhim narsa nima?",
                "options": [
                    "Qimmat kamera",
                    "Ko'p pul",
                    "Muntazam mashq qilish",
                    "Mashhur do'stlar"
                ],
                "correct": 2
            }
        ]
    },
    {
        "id": 3,
        "title": "Sun'iy intellekt qanday paydo bo'lgan?",
        "week": 2,
        "description": "AI tarixi - Alan Turingdan ChatGPTgacha",
        "tests": [
            {
                "question": "Sun'iy intellekt g'oyasini birinchi o'ylab topgan olim kim?",
                "options": ["Albert Eynshteyn", "Alan Turing", "Ishoq Nyuton", "Nikola Tesla"],
                "correct": 1
            },
            {
                "question": "ChatGPT qachon yaratilgan?",
                "options": ["2010-yil", "2015-yil", "2022-yil", "2000-yil"],
                "correct": 2
            },
            {
                "question": "Sun'iy intellekt qanday o'rganadi?",
                "options": [
                    "Kitob o'qib",
                    "Ko'p miqdordagi ma'lumotlardan",
                    "Televizor ko'rib",
                    "Uxlab"
                ],
                "correct": 1
            },
            {
                "question": "Murodjon ChatGPTga nima so'radi?",
                "options": [
                    "Ovqat retsepti",
                    "O'yin qoidasi",
                    "Seni kim yaratgan",
                    "Havo qanday"
                ],
                "correct": 2
            },
            {
                "question": "Sun'iy intellekt insondan qanday farq qiladi?",
                "options": [
                    "U hech qachon charchamaydi",
                    "U his-tuyg'ularga ega",
                    "U ovqat yeydi",
                    "U uxlaydi"
                ],
                "correct": 0
            }
        ]
    },
    {
        "id": 4,
        "title": "Ovoz va nutq mashqlari",
        "week": 2,
        "description": "Ovozimizni go'zal va aniq qilishni o'rganamiz",
        "tests": [
            {
                "question": "Nutq uchun eng muhim organ qaysi?",
                "options": ["Ko'z", "Quloq", "Og'iz va nafas", "Qo'l"],
                "correct": 2
            },
            {
                "question": "Sekin va tez gapirish mashqi nima uchun?",
                "options": [
                    "Nutq tezligini his qilish uchun",
                    "Uxlab qolmaslik uchun",
                    "Ovqat hazm qilish uchun",
                    "Yugurish uchun"
                ],
                "correct": 0
            },
            {
                "question": "Murodjon o'z ovozini birinchi marta eshitganda nima his qildi?",
                "options": [
                    "Hayron qoldi",
                    "Xafa bo'ldi",
                    "Uxlab qoldi",
                    "Kuldi"
                ],
                "correct": 0
            },
            {
                "question": "Yaxshi bloger uchun ovoz qanday bo'lishi kerak?",
                "options": [
                    "Juda baland",
                    "Aniq va qulay",
                    "Juda past",
                    "Qo'rqinchli"
                ],
                "correct": 1
            },
            {
                "question": "Nutq mashqida \"AEIOU\" nima?",
                "options": [
                    "Raqamlar",
                    "Unli tovushlar",
                    "Undosh tovushlar",
                    "O'yin nomi"
                ],
                "correct": 1
            }
        ]
    },
    {
        "id": 5,
        "title": "OpenAI startapi tarixi",
        "week": 3,
        "description": "Katta orzular qanday haqiqatga aylanadi",
        "tests": [
            {
                "question": "OpenAI kompaniyasi qachon tashkil etilgan?",
                "options": ["2010-yil", "2015-yil", "2020-yil", "2022-yil"],
                "correct": 1
            },
            {
                "question": "OpenAI kompaniyasini kim tashkil qilgan?",
                "options": [
                    "Bir kishi",
                    "Bir guruh do'stlar",
                    "Davlat",
                    "Bitta milliarder"
                ],
                "correct": 1
            },
            {
                "question": "Murodjon daftariga nima yozdi?",
                "options": [
                    "Maktab vazifasi",
                    "Ovqat retsepti",
                    "O'z g'oyalarini",
                    "Do'stlari ismini"
                ],
                "correct": 2
            },
            {
                "question": "Katta g'oyalar qanday boshlanadi?",
                "options": [
                    "Ko'p puldan",
                    "Shunchaki orzudan",
                    "Mashhurlikdan",
                    "Omaddan"
                ],
                "correct": 1
            },
            {
                "question": "Murodjonning birinchi g'oyasi nima edi?",
                "options": [
                    "Kompyuter sotib olish",
                    "Bolalar uchun qiziq kanal ochish",
                    "Maktabni tark etish",
                    "Chet elga ketish"
                ],
                "correct": 1
            }
        ]
    },
    {
        "id": 6,
        "title": "Yuz ifodalari va emotsiyalar",
        "week": 3,
        "description": "Kamera oldida his-tuyg'ularimizni ko'rsatishni o'rganamiz",
        "tests": [
            {
                "question": "Kamera oldida yuz ifodasi nima uchun muhim?",
                "options": [
                    "Chiroyli ko'rinish uchun",
                    "Tomoshabinlar bilan bog'lanish uchun",
                    "Ko'proq pul topish uchun",
                    "Kamerani aldash uchun"
                ],
                "correct": 1
            },
            {
                "question": "Murodjon kamera oldida kulishni mashq qilganda nima sezdi?",
                "options": [
                    "Qo'rquv",
                    "Erkinlik",
                    "Og'riq",
                    "Uyqu"
                ],
                "correct": 1
            },
            {
                "question": "Yaxshi bloger qanday bo'lishi kerak?",
                "options": [
                    "Doim jiddiy",
                    "Doim g'amgin",
                    "Tabiiy va samimiy",
                    "Doim kulgan"
                ],
                "correct": 2
            },
            {
                "question": "Emotsiyalarni ko'rsatish nima beradi?",
                "options": [
                    "Tomoshabinlar ko'proq tomosha qiladi",
                    "Kamera buziladi",
                    "Video qisqaradi",
                    "Hech narsa bermaydi"
                ],
                "correct": 0
            },
            {
                "question": "Kamera oldida qo'rquvni yengish uchun nima qilish kerak?",
                "options": [
                    "Kamerani o'chirish",
                    "Ko'p mashq qilish",
                    "Yig'lash",
                    "Qochish"
                ],
                "correct": 1
            }
        ]
    },
    {
        "id": 7,
        "title": "Google va Anthropic — kim ular?",
        "week": 4,
        "description": "Dunyo miqyosidagi AI kompaniyalari bilan tanishamiz",
        "tests": [
            {
                "question": "Anthropic kompaniyasi qaysi AI ni yaratgan?",
                "options": ["ChatGPT", "Gemini", "Claude", "Siri"],
                "correct": 2
            },
            {
                "question": "Google qaysi AI yordamchisini yaratgan?",
                "options": ["Claude", "ChatGPT", "Gemini", "Alexa"],
                "correct": 2
            },
            {
                "question": "Murodjon o'z g'oyasini topganda nima qildi?",
                "options": [
                    "Uxladi",
                    "Uyga qaytdi",
                    "Daftariga yozdi",
                    "Unutdi"
                ],
                "correct": 2
            },
            {
                "question": "Dunyo miqyosidagi kompaniyalar qayerda joylashgan?",
                "options": [
                    "Faqat Amerikada",
                    "Faqat Yaponiyada",
                    "Butun dunyoda",
                    "Faqat Yeropada"
                ],
                "correct": 2
            },
            {
                "question": "Sun'iy intellektni o'rganish nima beradi?",
                "options": [
                    "Hech narsa bermaydi",
                    "Kelajakda ko'p imkoniyatlar",
                    "Faqat o'yin imkoniyati",
                    "Vaqt sarflash"
                ],
                "correct": 1
            }
        ]
    },
    {
        "id": 8,
        "title": "Birinchi qisqa vlog",
        "week": 4,
        "description": "Birinchi videomizni tayyorlaymiz!",
        "tests": [
            {
                "question": "Yaxshi vlog uchun nima kerak?",
                "options": [
                    "Juda qimmat kamera",
                    "G'oya, ovoz va tabassum",
                    "Million dollar",
                    "Mashhur do'stlar"
                ],
                "correct": 1
            },
            {
                "question": "Birinchi vlog qancha uzun bo'lishi kerak?",
                "options": [
                    "1 soat",
                    "30 daqiqa",
                    "1 daqiqa",
                    "3 soat"
                ],
                "correct": 2
            },
            {
                "question": "Murodjon birinchi vlogida nima haqida gapirdi?",
                "options": [
                    "Ovqat haqida",
                    "O'zi haqida va AI haqida",
                    "Maktab haqida",
                    "Sport haqida"
                ],
                "correct": 1
            },
            {
                "question": "1 oyda siz nima o'rgandingiz?",
                "options": [
                    "Hech narsa",
                    "AI, ovoz, kamera va g'oya",
                    "Faqat o'yin",
                    "Faqat rasmlar"
                ],
                "correct": 1
            },
            {
                "question": "Bloger bo'lish uchun eng muhim qadam nima?",
                "options": [
                    "Boshlash",
                    "Kutish",
                    "Pul topish",
                    "Mashhur bo'lish"
                ],
                "correct": 0
            }
        ]
    }
]
