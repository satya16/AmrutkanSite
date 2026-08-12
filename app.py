import http.server
import socketserver
import os
import re
import urllib.parse
import html
import json
import logging
import zipfile
import gzip
from logging.handlers import RotatingFileHandler

AUDIO_DIR = os.path.expanduser("~/Desktop/अमृतकण")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
FRONTEND_DIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")
ZIP_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zip-cache")
ACCESS_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "access.log")
PORT = 8080
CHUNK_SIZE = 64 * 1024
PRIMARY_DOMAIN = "amrutkan.org"

access_logger = logging.getLogger("audio_site.access")
access_logger.setLevel(logging.INFO)
access_logger.propagate = False
_access_handler = RotatingFileHandler(ACCESS_LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
_access_handler.setFormatter(logging.Formatter("%(message)s"))
access_logger.addHandler(_access_handler)

AUDIO_EXTENSIONS = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
}

DEVANAGARI_DIGITS = "०१२३४५६७८९"
DIGIT_TRANS = str.maketrans(DEVANAGARI_DIGITS, "0123456789")
REV_DIGIT_TRANS = str.maketrans("0123456789", DEVANAGARI_DIGITS)
TOKEN_RE = re.compile(r"[0-9०-९]+|[^0-9०-९]+")

BOOK_DEFS = [
    {"id": "dnyaneshwari", "prefix": "श्री ज्ञानेश्वरी", "name": "श्री ज्ञानेश्वरी", "unit": "अध्याय"},
    {"id": "changdev", "prefix": "श्री चांगदेव पासष्टी", "name": "श्री चांगदेव पासष्टी", "unit": "ओवी"},
]
BOOKS_BY_ID = {b["id"]: b for b in BOOK_DEFS}

# Official logo path data + brand colors sourced from simple-icons (simpleicons.org),
# an open-source library of accurate brand marks. Verified brand colors against
# each platform's own guidelines where available.
PODCAST_LINKS = [
    {
        "label": "Spotify",
        "url": "https://open.spotify.com/show/0hLACcwC34Y4ESIjX59rHt?si=079a1d0abf634327",
        "color": "#1ED760",
        "path": "M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z",
    },
    {
        "label": "Apple Podcasts",
        "url": "https://podcasts.apple.com/in/podcast/%E0%A4%85%E0%A4%AE-%E0%A4%A4-%E0%A4%95%E0%A4%A3/id1838270896?l=hi",
        "color": "#9933CC",
        "path": "M5.34 0A5.328 5.328 0 000 5.34v13.32A5.328 5.328 0 005.34 24h13.32A5.328 5.328 0 0024 18.66V5.34A5.328 5.328 0 0018.66 0zm6.525 2.568c2.336 0 4.448.902 6.056 2.587 1.224 1.272 1.912 2.619 2.264 4.392.12.59.12 2.2.007 2.864a8.506 8.506 0 01-3.24 5.296c-.608.46-2.096 1.261-2.336 1.261-.088 0-.096-.091-.056-.46.072-.592.144-.715.48-.856.536-.224 1.448-.874 2.008-1.435a7.644 7.644 0 002.008-3.536c.208-.824.184-2.656-.048-3.504-.728-2.696-2.928-4.792-5.624-5.352-.784-.16-2.208-.16-3 0-2.728.56-4.984 2.76-5.672 5.528-.184.752-.184 2.584 0 3.336.456 1.832 1.64 3.512 3.192 4.512.304.2.672.408.824.472.336.144.408.264.472.856.04.36.03.464-.056.464-.056 0-.464-.176-.896-.384l-.04-.03c-2.472-1.216-4.056-3.274-4.632-6.012-.144-.706-.168-2.392-.03-3.04.36-1.74 1.048-3.1 2.192-4.304 1.648-1.737 3.768-2.656 6.128-2.656zm.134 2.81c.409.004.803.04 1.106.106 2.784.62 4.76 3.408 4.376 6.174-.152 1.114-.536 2.03-1.216 2.88-.336.43-1.152 1.15-1.296 1.15-.023 0-.048-.272-.048-.603v-.605l.416-.496c1.568-1.878 1.456-4.502-.256-6.224-.664-.67-1.432-1.064-2.424-1.246-.64-.118-.776-.118-1.448-.008-1.02.167-1.81.562-2.512 1.256-1.72 1.704-1.832 4.342-.264 6.222l.413.496v.608c0 .336-.027.608-.06.608-.03 0-.264-.16-.512-.36l-.034-.011c-.832-.664-1.568-1.842-1.872-2.997-.184-.698-.184-2.024.008-2.72.504-1.878 1.888-3.335 3.808-4.019.41-.145 1.133-.22 1.814-.211zm-.13 2.99c.31 0 .62.06.844.178.488.253.888.745 1.04 1.259.464 1.578-1.208 2.96-2.72 2.254h-.015c-.712-.331-1.096-.956-1.104-1.77 0-.733.408-1.371 1.112-1.745.224-.117.534-.176.844-.176zm-.011 4.728c.988-.004 1.706.349 1.97.97.198.464.124 1.932-.218 4.302-.232 1.656-.36 2.074-.68 2.356-.44.39-1.064.498-1.656.288h-.003c-.716-.257-.87-.605-1.164-2.644-.341-2.37-.416-3.838-.218-4.302.262-.616.974-.966 1.97-.97z",
    },
    {
        "label": "Amazon Music",
        "url": "https://music.amazon.in/podcasts/24c597b2-d34b-44df-9b64-d297461e37a5/%E0%A4%85%E0%A4%AE%E0%A5%83%E0%A4%A4%E2%80%8B%E2%80%8B%E0%A4%95%E0%A4%A3",
        "color": "#00A8E1",
        "path": "M14.8454 9.4083c-1.3907 1.0194-3.405 1.563-5.1424 1.563a9.333 9.333 0 0 1-6.2768-2.3835c-.1313-.117-.0143-.277.1415-.1846a12.693 12.693 0 0 0 6.285 1.6574c1.5384 0 3.2348-.318 4.7917-.9764.2359-.0985.4328.1538.203.324h-.002zm.5784-.6564c-.1784-.2257-1.1753-.1087-1.6225-.0554-.1374.0164-.158-.1026-.0349-.1867.796-.5558 2.0984-.3958 2.2502-.2092.1539.1867-.041 1.4872-.7856 2.1087-.1149.0964-.2236.0451-.1723-.082.1682-.4165.5436-1.3498.3651-1.5754zm-1.5917-4.1702v-.5394c0-.082.0615-.1375.1374-.1375h2.4348c.078 0 .1395.0554.1395.1354v.4636c0 .078-.0656.1805-.1846.3405L15.0997 6.635c.4677-.0102.9641.0595 1.3887.2974.0964.0534.123.1334.1292.2113v.5744c0 .082-.0882.1723-.1784.123a2.8163 2.8163 0 0 0-2.5723.0062c-.0861.0451-.1743-.0451-.1743-.1251v-.5477c0-.0882.002-.238.0902-.3713l1.4626-2.0881h-1.2718c-.078 0-.1415-.0534-.1436-.1354l.002.002zm4.808-.7466c1.0995 0 1.6944.9395 1.6944 2.1333 0 1.1528-.6564 2.0676-1.6943 2.0676-1.079 0-1.6656-.9395-1.6656-2.1087 0-1.1774.5948-2.0922 1.6656-2.0922zm.0062.7713c-.5456 0-.5805.7384-.5805 1.202 0 .4615-.0061 1.4481.5744 1.4481.5743 0 .601-.7958.601-1.282 0-.318-.0144-.6994-.1108-1.001-.082-.2625-.2482-.3671-.4841-.3671zm-6.008 3.3414c-.0493.041-.1395.0451-.1744.0164-.2543-.1949-.4246-.4923-.4246-.4923-.4061.4123-.6954.5374-1.2225.5374-.6215 0-1.1077-.3835-1.1077-1.1486a1.2512 1.2512 0 0 1 .7897-1.2041c.402-.1764.9641-.2072 1.3928-.2564 0 0 .0349-.4615-.0902-.6297a.521.521 0 0 0-.4164-.1908c-.2728 0-.5395.1477-.5928.4328-.0144.082-.0739.1518-.1395.1436L9.945 5.08a.1292.1292 0 0 1-.1108-.1537c.1641-.8657.9498-1.1282 1.6554-1.1282.361 0 .8307.0964 1.1158.3671.359.3344.3262.7795.3262 1.2677v1.1487c0 .3446.1436.4964.279.681.0471.0677.0574.1477-.002.197-.1519.125-.5703.4881-.5703.4881zm-.7467-1.7969v-.16c-.5353 0-1.1015.115-1.1015.7426 0 .318.1662.5333.4513.5333.2051 0 .3938-.1272.5128-.3344.1436-.2564.1374-.4943.1374-.7815zM2.9278 7.948c-.0472.041-.1375.045-.1723.0163-.2544-.1949-.4246-.4923-.4246-.4923-.4082.4123-.6954.5374-1.2226.5374-.6235 0-1.1076-.3835-1.1076-1.1486a1.2512 1.2512 0 0 1 .7897-1.2041c.402-.1764.964-.2072 1.3928-.2564 0 0 .0348-.4615-.0903-.6297a.521.521 0 0 0-.4164-.1908c-.2748 0-.5395.1477-.5928.4328-.0143.082-.0759.1518-.1395.1436L.2345 5.08a.1292.1292 0 0 1-.1087-.1537c.162-.8657.9497-1.1282 1.6553-1.1282.361 0 .8308.0964 1.1159.3671.359.3344.324.7795.324 1.2677v1.1487c0 .3446.1437.4964.279.681.0472.0677.0575.1477-.002.197-.1518.125-.5702.4881-.5702.4881zm-.7446-1.797v-.16c-.5354 0-1.1015.115-1.1015.7426 0 .318.164.5333.4512.5333.2052 0 .3939-.1272.5128-.3344.1436-.2564.1375-.4943.1375-.7815zm2.9127-.3343v2.002a.1379.1379 0 0 1-.1395.1374H4.218a.1374.1374 0 0 1-.1395-.1374v-3.766a.1379.1379 0 0 1 .1395-.1375h.6913a.1374.1374 0 0 1 .1374.1374v.482h.0143c.1805-.4758.519-.6994.9744-.6994.4636 0 .7528.2236.962.6995a1.0523 1.0523 0 0 1 1.0215-.6995c.3118 0 .6502.1272.8574.4143.236.318.1867.7795.1867 1.1857v2.3855c0 .076-.0636.1354-.1436.1354H8.181a.1374.1374 0 0 1-.1334-.1354v-2.004c0-.16.0144-.558-.0205-.7077-.0554-.2564-.2215-.3282-.4369-.3282a.4923.4923 0 0 0-.441.3118c-.076.1908-.0698.5087-.0698.724v2.0041c0 .076-.0635.1354-.1435.1354h-.7385a.1374.1374 0 0 1-.1333-.1354v-2.004c0-.4226.0677-1.042-.4574-1.042-.5334 0-.5128.603-.5128 1.042h.002zm16.8077 2.002a.1374.1374 0 0 1-.1374.1374h-.7405a.1374.1374 0 0 1-.1374-.1374v-3.766a.1374.1374 0 0 1 .1374-.1375h.683c.0821 0 .1396.0636.1396.1067v.5764h.0143c.2051-.517.4964-.7631 1.0092-.7631.3323 0 .6564.119.8636.4451.1928.3036.1928.8123.1928 1.1774V7.837a.1395.1395 0 0 1-.1415.119h-.7426a.1395.1395 0 0 1-.1313-.119V5.552c0-.763-.2933-.7856-.4635-.7856-.197 0-.357.1538-.4246.2953a1.7025 1.7025 0 0 0-.1231.722l.002 2.0349zM.1914 20.0582c-.1271 0-.1907-.0615-.1907-.1907v-4.4491c0-.1272.0636-.1908.1907-.1908H.616c.0616 0 .1129.0144.1477.039.0349.0246.0595.0738.0718.1436l.0575.3035c.6133-.4184 1.2102-.6276 1.7907-.6276.5948 0 .9969.2256 1.2081.6769.6318-.4513 1.2636-.677 1.8954-.677.441 0 .7794.1231 1.0153.3693.236.2502.3549.603.3549 1.0584v3.3538c0 .1271-.0656.1907-.1928.1907h-.5641c-.1272 0-.1928-.0615-.1928-.1907v-3.085c0-.318-.0616-.5539-.1805-.7057-.1231-.1538-.3139-.2297-.5744-.2297-.4677 0-.9353.1436-1.4092.4307a.997.997 0 0 1 .0103.1416v3.448c0 .1272-.0636.1908-.1908.1908H3.297c-.1272 0-.1908-.0615-.1908-.1907v-3.085c0-.318-.0615-.5539-.1825-.7057-.1231-.1538-.3139-.2297-.5744-.2297-.4861 0-.9517.1395-1.399.4205v3.5999c0 .1271-.0615.1907-.1907.1907H.1914zm9.731.1436c-.4533 0-.8-.1272-1.044-.3815-.242-.2544-.3631-.6133-.3631-1.0769v-3.321c0-.1292.0615-.1927.1908-.1927h.564c.1293 0 .1929.0635.1929.1907v3.0215c0 .3425.0656.5948.201.7569.1333.162.3487.242.642.242.4595 0 .923-.1518 1.3887-.4574v-3.565c0-.1272.0615-.1908.1908-.1908h.564c.1293 0 .1929.0636.1929.1908v4.4511c0 .1252-.0636.1887-.1928.1887h-.4103c-.0636 0-.1149-.0123-.1497-.0369-.0349-.0266-.0575-.0738-.0718-.1436l-.0657-.3323c-.5948.437-1.204.6564-1.8297.6564zm5.4399 0c-.5374 0-1.0195-.0882-1.4461-.2666a.3754.3754 0 0 1-.158-.1047c-.0287-.039-.043-.0984-.043-.1805v-.2687c0-.1148.0369-.1723.1148-.1723.0452 0 .1231.0205.238.0575.4225.1333.8615.199 1.3128.199.3138 0 .5517-.0616.7138-.1806.164-.121.244-.2954.244-.523a.4923.4923 0 0 0-.1476-.3734 1.606 1.606 0 0 0-.5415-.285l-.8144-.3037c-.7097-.2605-1.0625-.7056-1.0625-1.3333 0-.4143.16-.7487.484-1.001.3221-.2543.7447-.3815 1.2677-.3815a3.487 3.487 0 0 1 1.2164.2195c.076.0246.1313.0574.1641.0985.0308.041.0472.1025.0472.1846v.2584c0 .1149-.041.1723-.123.1723a.8615.8615 0 0 1-.2216-.0472 3.5495 3.5495 0 0 0-1.0359-.1538c-.6112 0-.919.2072-.919.6195 0 .164.0514.2953.154.3897.1025.0964.3035.201.603.3159l.7466.2872c.3774.1436.6482.318.8144.519.1661.1989.2482.4574.2482.7753 0 .4513-.1682.8102-.5067 1.0769-.3385.2666-.7877.4-1.3497.4v.002zm3.0645-.1436c-.1272 0-.1928-.0615-.1928-.1907v-4.4491c0-.1272.0656-.1908.1928-.1908h.5641c.1272 0 .1928.0636.1928.1908v4.4511c0 .1251-.0656.1887-.1928.1887h-.564zm.2872-5.688c-.1846 0-.3303-.0513-.437-.1559a.558.558 0 0 1-.1579-.4143c0-.1724.0534-.3098.158-.4144a.5907.5907 0 0 1 .4369-.158c.1846 0 .3282.0534.4349.158.1066.1026.1579.242.1579.4144 0 .1702-.0513.3076-.158.4143-.1046.1026-.2502.1559-.4348.1559z",
    },
    {
        "label": "WhatsApp",
        "url": "https://chat.whatsapp.com/D1x1Vr8TkYvCLituKh26so?s=cl&p=i&ilr=0",
        "color": "#25D366",
        "path": "M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.148-.669.148-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.017-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.148.198 2.096 3.2 5.077 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z",
    },
]

YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@%E0%A4%85%E0%A4%AE%E0%A5%83%E0%A4%A4%E0%A4%95%E0%A4%A3"
YOUTUBE_CHANNEL_HANDLE = "@अमृतकण"
YOUTUBE_VIDEO_IDS = ["8jccc3XVnkk", "lmKCjw8zdkw"]
# Brand icon path + color sourced from simple-icons, same convention as PODCAST_LINKS above.
YOUTUBE_ICON_PATH = "M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"
YOUTUBE_ICON_COLOR = "#FF0000"

ABOUT_TEXT_MR = (
    "अमृतकण हे चॅनल ज्ञान, कर्म आणि उपासना या आध्यात्मिक मार्गावर वाटचाल "
    "करणाऱ्यांवर महाराष्ट्रातील थोर संतांच्या दैवी आशीर्वादांचा वर्षाव करते. "
    "महाराष्ट्र ही एक पुण्यभूमी आहे, जिथे भूतकाळात अनेक संत जन्माला आले. या "
    "संतांनी मोक्षाच्या मार्गावर अत्यंत उच्च आध्यात्मिक मूल्ये रुजवली. या पवित्र "
    "आणि पावन आत्म्यांचे महान कार्य आजच्या धकाधकीच्या जीवनाला साजेशा छोट्या "
    "क्लिप्सच्या स्वरूपात पोहोचवण्याचा अमृतकणचा हा एक छोटासा प्रयत्न आहे. चला, "
    "अमृतकणसोबत या आध्यात्मिक प्रवासाला सुरुवात करूया."
)

ABOUT_ME_TEXT_MR = (
    "डॉ. सुरेश कुमार चौधरी (सुरेश चौधरी) यांचा जन्म मध्य प्रदेशात पांढुर्णाजवळ "
    "टीगाव येथे एका वारकरी कुटुंबात झाला. लहान वयातच गीता, ज्ञानेश्वरी व एकनाथी "
    "भागवत या ग्रंथांचा वसा लाभल्यामुळे मराठी संत साहित्याची त्यांना गोडी निर्माण "
    "झाली. व्यवसायाने कृषी वैज्ञानिक असल्यामुळे भारतीय कृषी अनुसंधान परिषदेच्या "
    "(ICAR) अनेक संस्थांमध्ये त्यांनी निरनिराळ्या पदांवर कार्य केले. मागील १२ "
    "वर्षांपासून ते नवी दिल्लीतील ICAR च्या मुख्यालयात वरिष्ठ पदांवर कार्य करत "
    "होते. मागील २ वर्षांपासून ते भारतीय उर्वरक संघामध्ये डायरेक्टर जनरल या "
    "पदावर कार्य करीत आहेत. आपल्या व्यवसायाव्यतिरिक्त त्यांना संत साहित्य तथा "
    "भारतीय शास्त्रीय संगीताची अभिरुची आहे. \"सोपी गीता\" आणि \"चैतन्य सागर\" या "
    "त्यांच्या साहित्यकृती आहेत. त्यांनी याआधी काही अभंग, भजन व आरत्याही रचल्या "
    "आहेत."
)


def to_int(s):
    return int(s.translate(DIGIT_TRANS))


def to_devanagari(n):
    return str(n).translate(REV_DIGIT_TRANS)


def natural_sort_key(s):
    key = []
    for tok in TOKEN_RE.findall(s):
        if tok[0] in "0123456789०१२३४५६७८९":
            key.append((0, to_int(tok)))
        else:
            key.append((1, tok))
    return key


def discover_audio_files():
    """Recursively scan AUDIO_DIR so files can live directly in it or in subfolders."""
    mapping = {}
    for root, _dirs, files in os.walk(AUDIO_DIR):
        for f in files:
            if os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS:
                mapping[f] = os.path.join(root, f)
    return mapping


FILES_BY_NAME = discover_audio_files()


def list_audio_files():
    return sorted(FILES_BY_NAME.keys())


# For these books, certain "इतर"-bucket files (a single-episode intro,
# summary, or short biography) get pulled out and placed as their own
# individually-labelled tiles at specific positions relative to the numbered
# chapters, instead of being lumped into one generic "इतर" tile. Order within
# "lead"/"trail" is the order they're shown in.
SPECIAL_CHAPTER_ORDER = {
    "dnyaneshwari": {
        "lead": [("परिचय", "parichay")],
        "trail": [("सिंहावलोकन", "sinhavalokan")],
    },
    "changdev": {
        "lead": [
            ("श्री चांगदेवांचे संक्षिप्त चरित्र", "changdev_charitra"),
            ("श्री ज्ञानेश्वरांचे संक्षिप्त चरित्र", "dnyaneshwar_charitra"),
            ("सारांश", "saransh"),
        ],
        "trail": [],
    },
}


def build_library():
    files = list_audio_files()
    library = {}
    for book in BOOK_DEFS:
        pattern = re.compile(re.escape(book["unit"]) + r"\s+([0-9०-९]+)")
        chapters = {}
        for f in files:
            name = os.path.splitext(f)[0]
            if not name.startswith(book["prefix"]):
                continue
            rest = name[len(book["prefix"]):].lstrip(" -")
            m = pattern.search(rest)
            if m:
                key = to_int(m.group(1))
                label = pattern.sub("", rest, count=1).strip(" -")
                if not label:
                    label = "मुख्य भाग"
            else:
                key = "other"
                label = rest.strip(" -")
            chapters.setdefault(key, []).append((f, label))

        lead_keys, trail_keys = [], []
        special = SPECIAL_CHAPTER_ORDER.get(book["id"])
        if special and "other" in chapters:
            other_by_label = {item[1]: item for item in chapters["other"]}
            remaining = list(chapters["other"])
            for label, key in special["lead"]:
                if label in other_by_label:
                    chapters[key] = [other_by_label[label]]
                    lead_keys.append(key)
                    remaining.remove(other_by_label[label])
            for label, key in special["trail"]:
                if label in other_by_label:
                    chapters[key] = [other_by_label[label]]
                    trail_keys.append(key)
                    remaining.remove(other_by_label[label])
            if remaining:
                chapters["other"] = remaining
            else:
                del chapters["other"]

        for key in chapters:
            # सारांश goes first within a chapter, ahead of श्लोक/ओवी/नमन etc.
            chapters[key].sort(
                key=lambda item: (0 if item[1].startswith("सारांश") else 1, natural_sort_key(item[1]))
            )
        numeric_keys = sorted(k for k in chapters if isinstance(k, int))
        order = lead_keys + numeric_keys + trail_keys + (["other"] if "other" in chapters else [])
        library[book["id"]] = {
            "name": book["name"],
            "unit": book["unit"],
            "chapters": chapters,
            "order": order,
        }
    return library


LIBRARY = build_library()

SITE_DESCRIPTION = "ज्ञानेश्वरी आणि इतर मराठी ग्रंथांचं निरूपण — ध्वनिरूपात ऐका"

GA_MEASUREMENT_ID = "G-KLHSC2QRRW"
GA_SNIPPET = f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_MEASUREMENT_ID}');
</script>"""

_ASSET_TAG_RE = re.compile(r'<(?:script|link)[^>]+/assets/[^>]+>(?:</script>)?')


def _load_frontend_asset_tags():
    """Extract the built <script>/<link> tags from the Vite build's own
    index.html, so app.py doesn't need to know the content-hashed filenames
    (frontend/dist/assets/index-<hash>.js etc) — just re-embed whatever the
    last `npm run build` produced."""
    index_path = os.path.join(FRONTEND_DIST_DIR, "index.html")
    try:
        with open(index_path, encoding="utf-8") as f:
            index_html = f.read()
    except FileNotFoundError:
        return ""
    return "\n".join(_ASSET_TAG_RE.findall(index_html))


FRONTEND_ASSET_TAGS = _load_frontend_asset_tags()


def spa_shell(title, base_url=""):
    """The HTML shell for every route the React app owns (/, /book/<id>,
    /book/<id>/<slug>) — Python still generates per-route <title>/og:* tags
    (so link previews work) but the actual page content is rendered
    client-side by React after it mounts into #root."""
    og_tags = ""
    if base_url:
        image_url = html.escape(f"{base_url}/static/mauli.jpg?v=2")
        og_tags = f"""
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(SITE_DESCRIPTION)}">
<meta property="og:image" content="{image_url}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">"""
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(SITE_DESCRIPTION)}">
<link rel="icon" href="/static/mauli.jpg?v=2" type="image/jpeg">
<link rel="apple-touch-icon" href="/static/mauli.jpg?v=2">{og_tags}
{GA_SNIPPET}
</head>
<body>
<div id="root"></div>
{FRONTEND_ASSET_TAGS}
</body>
</html>"""


SPECIAL_CHAPTER_LABELS = {
    key: label
    for special in SPECIAL_CHAPTER_ORDER.values()
    for label, key in special["lead"] + special["trail"]
}


def build_book_zip_items(book_id):
    """(display name, [(arcname, filepath), ...]) for every episode in a book,
    in the same order shown on the book page, grouped into per-chapter
    folders inside the zip so the extracted layout mirrors the site."""
    if book_id not in LIBRARY:
        raise LookupError(book_id)
    lib = LIBRARY[book_id]
    items = []
    for key in lib["order"]:
        if key == "other":
            label = "इतर"
        elif key in SPECIAL_CHAPTER_LABELS:
            label = SPECIAL_CHAPTER_LABELS[key]
        else:
            label = f"{lib['unit']} {to_devanagari(key)}"
        for filename, _label in lib["chapters"][key]:
            filepath = FILES_BY_NAME.get(filename)
            if filepath:
                items.append((f"{label}/{filename}", filepath))
    return lib["name"], items


def build_chapter_zip_items(book_id, slug):
    """Same as build_book_zip_items but scoped to one chapter/verse, flat
    (no subfolder) since it's already a single unit."""
    if book_id not in LIBRARY:
        raise LookupError(book_id)
    lib = LIBRARY[book_id]
    if slug == "other":
        key, chapter_label = "other", "इतर"
    elif slug in SPECIAL_CHAPTER_LABELS:
        key, chapter_label = slug, SPECIAL_CHAPTER_LABELS[slug]
    else:
        try:
            key = int(slug)
        except ValueError:
            raise LookupError(slug)
        chapter_label = f"{lib['unit']} {to_devanagari(key)}"
    if key not in lib["chapters"]:
        raise LookupError(slug)
    items = []
    for filename, _label in lib["chapters"][key]:
        filepath = FILES_BY_NAME.get(filename)
        if filepath:
            items.append((filename, filepath))
    return f"{chapter_label} - {lib['name']}", items


def api_home():
    """Static home-page content (about text, podcast/YouTube links) as JSON,
    consumed by the React web frontend's Home page."""
    return {
        "tagline": "ज्ञानेश्वरी आणि इतर मराठी ग्रंथांचं निरूपण",
        "siteDescription": SITE_DESCRIPTION,
        "heroImage": "/static/mauli.jpg?v=2",
        "aboutText": ABOUT_TEXT_MR,
        "aboutMePhoto": "/static/sk_chaudhari.jpg",
        "aboutMeText": ABOUT_ME_TEXT_MR,
        "podcastLinks": PODCAST_LINKS,
        "youtube": {
            "channelUrl": YOUTUBE_CHANNEL_URL,
            "channelHandle": YOUTUBE_CHANNEL_HANDLE,
            "videoIds": YOUTUBE_VIDEO_IDS,
        },
    }


def api_library():
    """Full library tree as JSON — consumed by both the React web frontend
    and the native AmrutkanApp (Expo/React Native), which can't scrape HTML."""
    books = []
    for book in BOOK_DEFS:
        lib = LIBRARY[book["id"]]
        chapters = []
        for key in lib["order"]:
            items = lib["chapters"][key]
            if key == "other":
                slug, label, is_special = "other", "इतर", True
            elif key in SPECIAL_CHAPTER_LABELS:
                slug, label, is_special = key, SPECIAL_CHAPTER_LABELS[key], True
            else:
                slug = str(key)
                label = f"{lib['unit']} {to_devanagari(key)}"
                is_special = False
            episodes = [
                {
                    "filename": filename,
                    "label": ep_label,
                    "audioUrl": f"/audio/{urllib.parse.quote(filename)}",
                }
                for filename, ep_label in items
            ]
            chapters.append({
                "slug": slug,
                "label": label,
                "isSpecial": is_special,
                "episodeCount": len(items),
                "episodes": episodes,
            })
        books.append({
            "id": book["id"],
            "name": lib["name"],
            "unit": lib["unit"],
            "totalEpisodes": sum(len(v) for v in lib["chapters"].values()),
            "chapters": chapters,
        })
    return {"books": books, "artworkUrl": "/static/mauli.jpg?v=2"}


class _NonSeekableWriter:
    """Wraps the response socket's file object so zipfile.ZipFile streams
    straight through it instead of buffering: ZipFile falls back to writing
    data descriptors (size/CRC after each entry) rather than seeking back to
    patch local file headers whenever fp.tell()/seek() aren't available, which
    a plain write-only socket stream satisfies for free. Needed because a
    full-book zip can be several GB - it must never be assembled in memory or
    on disk first."""

    def __init__(self, raw):
        self._raw = raw

    def write(self, data):
        self._raw.write(data)
        return len(data)

    def flush(self):
        pass


class AudioHandler(http.server.BaseHTTPRequestHandler):
    server_version = "AudioSite/2.0"
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        host = self.headers.get("Host", "").split(":")[0].lower()
        if host == f"www.{PRIMARY_DOMAIN}":
            self.send_response(301)
            self.send_header("Location", f"https://{PRIMARY_DOMAIN}{self.path}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        parts = [p for p in path.split("/") if p]
        try:
            if not parts:
                self.serve_spa_page("अमृतकण")
            elif parts[0] == "static" and len(parts) == 2:
                self.serve_static(parts[1])
            elif parts[0] == "assets" and len(parts) == 2:
                self.serve_frontend_asset(parts[1])
            elif parts[0] == "audio" and len(parts) == 2:
                self.serve_audio(parts[1])
            elif parts[0] == "api" and len(parts) == 2 and parts[1] == "library":
                self.serve_json(api_library())
            elif parts[0] == "api" and len(parts) == 2 and parts[1] == "home":
                self.serve_json(api_home())
            elif parts[0] == "download" and len(parts) == 3 and parts[1] == "book":
                display_name, items = build_book_zip_items(parts[2])
                cached = os.path.join(ZIP_CACHE_DIR, "book", f"{parts[2]}.zip")
                ascii_name, disp = f"{parts[2]}.zip", f"{display_name}.zip"
                if os.path.isfile(cached):
                    self.serve_cached_zip(cached, ascii_name, disp)
                else:
                    self.serve_zip(ascii_name, disp, items)
            elif parts[0] == "download" and len(parts) == 4 and parts[1] == "book":
                display_name, items = build_chapter_zip_items(parts[2], parts[3])
                cached = os.path.join(ZIP_CACHE_DIR, "book", parts[2], f"{parts[3]}.zip")
                ascii_name, disp = f"{parts[2]}-{parts[3]}.zip", f"{display_name}.zip"
                if os.path.isfile(cached):
                    self.serve_cached_zip(cached, ascii_name, disp)
                else:
                    self.serve_zip(ascii_name, disp, items)
            elif parts[0] == "book" and len(parts) == 2:
                if parts[1] not in LIBRARY:
                    raise LookupError(parts[1])
                self.serve_spa_page(LIBRARY[parts[1]]["name"])
            elif parts[0] == "book" and len(parts) == 3:
                # build_chapter_zip_items both validates the slug (LookupError
                # for 404) and already computes this exact title string — no
                # need to duplicate that resolution logic here.
                title, _items = build_chapter_zip_items(parts[1], parts[2])
                self.serve_spa_page(title)
            else:
                self.send_error(404)
        except LookupError:
            self.send_error(404)

    def serve_spa_page(self, title):
        host = self.headers.get("Host", "")
        base_url = ""
        if host:
            scheme = "http" if host.startswith("localhost") or host.startswith("127.") else "https"
            base_url = f"{scheme}://{host}"
        self.serve_html(spa_shell(title, base_url))

    def maybe_gzip(self, body):
        """gzip-compress a text-based response body when the client says it
        accepts gzip. Only called for text/JSON/JS/CSS — never for images,
        audio, or ZIPs, which are already-compressed binary formats where
        gzip would just burn CPU for no size win (or, for Range-requested
        audio, actively break byte-range semantics). Returns
        (possibly-compressed body, "gzip" or None) — caller sets headers."""
        if len(body) < 512:
            return body, None
        if "gzip" not in self.headers.get("Accept-Encoding", ""):
            return body, None
        return gzip.compress(body, compresslevel=6), "gzip"

    def send_compressible(self, body, content_type, extra_headers=None):
        body, encoding = self.maybe_gzip(body)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        if encoding:
            self.send_header("Content-Encoding", encoding)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def serve_html(self, body_str):
        self.send_compressible(body_str.encode("utf-8"), "text/html; charset=utf-8")

    def serve_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_compressible(body, "application/json; charset=utf-8")

    def serve_static(self, filename):
        safe = os.path.basename(filename)
        filepath = os.path.join(STATIC_DIR, safe)
        if not os.path.isfile(filepath):
            self.send_error(404)
            return
        ext = os.path.splitext(safe)[1].lower()
        ctype = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, "application/octet-stream")
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(data)

    def serve_frontend_asset(self, filename):
        safe = os.path.basename(filename)
        filepath = os.path.join(FRONTEND_DIST_DIR, "assets", safe)
        if not os.path.isfile(filepath):
            self.send_error(404)
            return
        ext = os.path.splitext(safe)[1].lower()
        ctype = {
            ".js": "application/javascript",
            ".css": "text/css",
            ".svg": "image/svg+xml",
            ".woff": "font/woff",
            ".woff2": "font/woff2",
        }.get(ext, "application/octet-stream")
        with open(filepath, "rb") as f:
            data = f.read()
        # Vite content-hashes these filenames, so a hit is immutable forever.
        cache_header = {"Cache-Control": "public, max-age=31536000, immutable"}
        # .woff/.woff2 are already-compressed binary font formats — gzip
        # would just cost CPU for no size win, same reasoning as audio/images.
        if ext in (".js", ".css", ".svg"):
            self.send_compressible(data, ctype, extra_headers=cache_header)
        else:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            for key, value in cache_header.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

    def serve_audio(self, filename):
        safe_name = os.path.basename(filename)
        filepath = FILES_BY_NAME.get(safe_name)
        ext = os.path.splitext(safe_name)[1].lower()
        content_type = AUDIO_EXTENSIONS.get(ext)
        if filepath is None or content_type is None or not os.path.isfile(filepath):
            self.send_error(404)
            return

        file_size = os.path.getsize(filepath)
        range_header = self.headers.get("Range")

        start, end = 0, file_size - 1
        status = 200
        if range_header:
            status = 206
            try:
                _, rng = range_header.split("=")
                start_str, end_str = rng.split("-")
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                end = min(end, file_size - 1)
            except (ValueError, IndexError):
                start, end = 0, file_size - 1

        length = end - start + 1
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(length))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.end_headers()

            with open(filepath, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def serve_cached_zip(self, filepath, ascii_name, display_name):
        """Serves a pre-built ZIP straight from disk (see zip-cache/,
        populated by build_zip_cache.py) — a real file with a known size, so
        unlike serve_zip() below this can send a real Content-Length and the
        browser shows file size/progress during download."""
        file_size = os.path.getsize(filepath)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(file_size))
            self.send_header(
                "Content-Disposition",
                f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{urllib.parse.quote(display_name)}",
            )
            self.end_headers()
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def serve_zip(self, ascii_name, display_name, items):
        """Streams a ZIP of the given (arcname, filepath) pairs directly to
        the client, uncompressed (ZIP_STORED - the mp3/m4a sources are already
        compressed, so re-compressing would only cost CPU for no size win).
        Fallback path used only when zip-cache/ doesn't have this book/chapter
        pre-built yet (see build_zip_cache.py) — e.g. right after new audio
        content is added but before the cache script has been re-run.
        No Content-Length is sent since the total size isn't known upfront
        without a first pass over every file; sending Connection: close
        instead lets the client treat the socket closing as end-of-body, which
        is standard HTTP/1.1 behaviour when Content-Length/chunked aren't used."""
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header(
                "Content-Disposition",
                f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{urllib.parse.quote(display_name)}",
            )
            self.send_header("Connection", "close")
            self.end_headers()
            with zipfile.ZipFile(_NonSeekableWriter(self.wfile), "w", zipfile.ZIP_STORED) as zf:
                for arcname, filepath in items:
                    zf.write(filepath, arcname=arcname)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, fmt, *args):
        # Every request arrives from cloudflared on localhost, so
        # client_address is always 127.0.0.1 — the real visitor IP is in the
        # CF-Connecting-IP header Cloudflare adds on every proxied request.
        # self.headers may not be set yet if this fires from a malformed
        # request that failed to parse, hence the getattr guard.
        headers = getattr(self, "headers", None)
        ip = (headers.get("CF-Connecting-IP") if headers else None) or self.client_address[0]
        access_logger.info(
            "%s [%s] %s",
            ip,
            self.log_date_time_string(),
            fmt % args,
        )


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 128


if __name__ == "__main__":
    total_files = sum(len(v) for lib in LIBRARY.values() for v in lib["chapters"].values())
    print(f"Serving {total_files} tracks across {len(LIBRARY)} books on port {PORT}")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), AudioHandler)
    server.serve_forever()
