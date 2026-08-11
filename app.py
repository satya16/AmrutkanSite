import http.server
import socketserver
import os
import re
import urllib.parse
import html
import json
import logging
import zipfile
from logging.handlers import RotatingFileHandler

AUDIO_DIR = os.path.expanduser("~/Desktop/अमृतकण")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
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

BASE_CSS = """
:root {
  --bg: #fdf6ec;
  --card: #ffffff;
  --ink: #3a2a1a;
  --accent: #b5541a;
  --accent-dark: #7c2d12;
  --accent-soft: #f6e2c4;
  --border: #ecd9b8;
  --shadow: 0 4px 16px rgba(124, 45, 18, 0.08);
  --ease-sheet: cubic-bezier(0.32, 0.72, 0, 1);
  color-scheme: light;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: 'Noto Sans Devanagari', 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--ink);
}
a { color: inherit; text-decoration: none; }
.topbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: var(--card);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 20;
}
.topbar img {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  object-position: top;
  border: 2px solid var(--accent-soft);
}
.topbar .site-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--accent-dark);
}
.container {
  max-width: 880px;
  margin: 0 auto;
  padding: 24px 18px 60px;
}
.breadcrumb {
  font-size: 0.9rem;
  margin-bottom: 20px;
  opacity: 0.8;
}
.breadcrumb a { color: var(--accent-dark); }
.breadcrumb a:hover { text-decoration: underline; }
.hero {
  text-align: center;
  padding: 24px 0 8px;
}
.hero img {
  width: 190px;
  height: 190px;
  border-radius: 50%;
  object-fit: cover;
  object-position: top;
  box-shadow: var(--shadow);
  border: 4px solid var(--card);
  outline: 3px solid var(--accent-soft);
}
.hero h1 {
  font-size: 2.2rem;
  margin: 18px 0 4px;
  color: var(--accent-dark);
}
.hero p.tagline {
  margin: 0 0 30px;
  opacity: 0.75;
  font-size: 1rem;
}
.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-top: 10px;
}
.book-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 28px 20px;
  text-align: center;
  box-shadow: var(--shadow);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.book-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 22px rgba(124, 45, 18, 0.14);
}
.podcast-footer {
  margin-top: 44px;
  padding-top: 26px;
  border-top: 1px solid var(--border);
  text-align: center;
}
.podcast-footer-title {
  font-size: 0.85rem;
  opacity: 0.6;
  margin-bottom: 14px;
}
.podcast-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}
.podcast-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 20px 6px 6px;
  border-radius: 999px;
  background: var(--card);
  border: 1px solid var(--border);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--accent-dark);
  box-shadow: var(--shadow);
  transition: background 0.12s ease, transform 0.12s ease;
}
.podcast-link:hover { background: var(--accent-soft); transform: translateY(-2px); }
.podcast-icon {
  width: 34px;
  height: 34px;
  min-width: 34px;
  border-radius: 50%;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.podcast-icon svg { width: 19px; height: 19px; }
.book-card h2 {
  margin: 0 0 6px;
  font-size: 1.25rem;
  color: var(--accent-dark);
}
.book-card .count {
  font-size: 0.85rem;
  opacity: 0.65;
}
.home-scroll {
  display: flex;
  flex-direction: column;
  gap: 28px;
  scroll-snap-type: y proximity;
}
.home-section {
  scroll-snap-align: start;
  scroll-margin-top: 76px;
}
.section-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 32px 24px;
  box-shadow: var(--shadow);
  min-height: 60vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.section-title {
  font-size: 1.5rem;
  color: var(--accent-dark);
  margin: 0 0 6px;
  text-align: center;
}
.section-lead {
  text-align: center;
  opacity: 0.7;
  margin: 0 0 22px;
}
.yt-channel-link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 10px 22px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-dark);
  font-weight: 600;
  margin: 0 auto 26px;
  width: fit-content;
  box-shadow: var(--shadow);
}
.yt-channel-link svg { width: 22px; height: 22px; flex-shrink: 0; }
.yt-video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 18px;
}
.yt-embed {
  width: 100%;
  aspect-ratio: 16 / 9;
  border: 0;
  border-radius: 14px;
  box-shadow: var(--shadow);
}
.about-text {
  max-width: 640px;
  margin: 0 auto;
  font-size: 1.05rem;
  line-height: 1.9;
  text-align: center;
}
.about-me {
  max-width: 640px;
  margin: 28px auto 0;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}
.about-me-title {
  font-size: 1.15rem;
  color: var(--accent-dark);
  margin: 0 0 16px;
  text-align: center;
}
.about-me-row {
  display: flex;
  align-items: flex-start;
  gap: 24px;
}
.about-me-photo {
  flex-shrink: 0;
  width: 140px;
  height: 180px;
  object-fit: cover;
  border-radius: 14px;
  box-shadow: var(--shadow);
  border: 3px solid var(--card);
  outline: 2px solid var(--accent-soft);
}
.about-me-text {
  flex: 1;
  min-width: 0;
  line-height: 1.8;
}
@media (max-width: 600px) {
  .section-card { padding: 24px 16px; min-height: 0; }
  .about-me-row { flex-direction: column; align-items: center; text-align: center; }
}
@media (prefers-reduced-motion: reduce) {
  .home-scroll { scroll-snap-type: none; }
}
h1.page-title {
  font-size: 1.6rem;
  color: var(--accent-dark);
  margin: 0 0 20px;
}
.tile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 12px;
}
.tile {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 8px;
  text-align: center;
  box-shadow: var(--shadow);
  transition: transform 0.12s ease, background 0.12s ease;
}
.tile:hover { transform: translateY(-2px); background: var(--accent-soft); }
.tile .num {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--accent-dark);
}
.tile .badge {
  font-size: 0.75rem;
  opacity: 0.6;
  margin-top: 4px;
}
.tile.other .num { font-size: 0.95rem; }
.tile-icon {
  display: flex;
  justify-content: center;
  opacity: 0.35;
  margin-bottom: 5px;
}
.tile-icon svg { width: 14px; height: 14px; display: block; }
.page-actions { margin: -8px 0 20px; }
.download-all-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 999px;
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--accent-dark);
  font-size: 0.85rem;
  font-weight: 600;
  box-shadow: var(--shadow);
}
.download-all-btn:hover { background: var(--accent-soft); transform: translateY(-2px); }
.download-all-btn svg { width: 15px; height: 15px; display: block; flex-shrink: 0; }
#search {
  width: 100%;
  padding: 10px 12px;
  font-size: 1rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  margin: 4px 0 14px;
  background: var(--card);
  color: var(--ink);
}
ul.episode-list { list-style: none; padding: 0; margin: 0; }
li.track {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 14px;
  margin-bottom: 8px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--card);
  cursor: pointer;
}
li.track:hover { background: var(--accent-soft); }
li.track.playing {
  border-color: var(--accent);
  background: var(--accent-soft);
  font-weight: 600;
}
.track-label { flex: 1; min-width: 0; }
.dl-btn {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: var(--accent-dark);
  opacity: 0.7;
}
.dl-btn:hover { opacity: 1; background: var(--accent-soft); }
.dl-btn svg { width: 16px; height: 16px; display: block; }
#count { font-size: 0.85rem; opacity: 0.65; margin-bottom: 10px; }

[data-theme="dark"] {
  --bg: #17110b;
  --card: #241b12;
  --ink: #f1e3ce;
  --accent: #e08c3e;
  --accent-dark: #f0a962;
  --accent-soft: #3a2a17;
  --border: #3d2c1a;
  --shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  color-scheme: dark;
}

.theme-toggle {
  margin-left: auto;
  width: 40px;
  height: 40px;
  min-width: 40px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--ink);
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.topbar-link {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.topbar-link .site-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

#content { padding-bottom: 100px; transition: opacity 0.15s ease; }
#content.fading { opacity: 0; }

.player-shell {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 30;
  background: var(--card);
  border-top: 1px solid var(--border);
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.12);
  padding-bottom: env(safe-area-inset-bottom, 0);
  transform: translateY(100%);
  transition: transform 0.32s var(--ease-sheet);
}
.player-shell.active { transform: translateY(0); }
.mini-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  cursor: pointer;
}
.play-toggle {
  width: 42px;
  height: 42px;
  min-width: 42px;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 1.05rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  cursor: pointer;
}
.mini-info { flex: 1; min-width: 0; }
.now-label {
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.progress-track {
  height: 3px;
  background: var(--border);
  border-radius: 2px;
  margin-top: 7px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  width: 0%;
  background: var(--accent);
}
.expand-toggle {
  background: none;
  border: none;
  font-size: 1.1rem;
  color: var(--accent-dark);
  cursor: pointer;
  flex-shrink: 0;
  padding: 6px;
}
#player { display: none; }

.now-playing-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg);
  z-index: 40;
  display: flex;
  flex-direction: column;
  transform: translateY(100%);
  transition: transform 0.4s var(--ease-sheet);
  padding-top: env(safe-area-inset-top, 0);
  padding-bottom: env(safe-area-inset-bottom, 0);
}
.now-playing-overlay.open { transform: translateY(0); }
.np-header {
  display: flex;
  align-items: center;
  padding: 14px 8px;
  gap: 10px;
  flex-shrink: 0;
}
.np-collapse {
  background: none;
  border: none;
  font-size: 1.7rem;
  line-height: 1;
  color: var(--ink);
  cursor: pointer;
  padding: 8px 14px;
}
.np-header-title {
  flex: 1;
  text-align: center;
  font-size: 0.8rem;
  opacity: 0.55;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.np-header-spacer { width: 46px; flex-shrink: 0; }
.np-art-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 32px;
  min-height: 0;
}
.np-art {
  width: min(72vw, 320px);
  height: min(72vw, 320px);
  object-fit: cover;
  object-position: top;
  border-radius: 22px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.22);
}
.np-meta {
  text-align: center;
  padding: 4px 28px 6px;
  flex-shrink: 0;
}
.np-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--accent-dark);
  margin-bottom: 4px;
  overflow-wrap: break-word;
}
.np-subtitle {
  font-size: 0.9rem;
  opacity: 0.65;
}
.np-progress {
  padding: 18px 26px 0;
  flex-shrink: 0;
}
.np-seek {
  width: 100%;
  accent-color: var(--accent);
  cursor: pointer;
}
.np-time-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  opacity: 0.6;
  margin-top: 2px;
}
.np-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 32px;
  padding: 18px 24px 34px;
  flex-shrink: 0;
}
.np-side-btn {
  background: none;
  border: none;
  font-size: 1.6rem;
  color: var(--accent-dark);
  cursor: pointer;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.np-side-btn:disabled { opacity: 0.3; cursor: default; }
.np-play-btn {
  width: 68px;
  height: 68px;
  min-width: 68px;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow);
}
.play-toggle svg, .np-play-btn svg, .np-side-btn svg {
  width: 1em;
  height: 1em;
  display: block;
}
.np-secondary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 24px 26px;
  flex-shrink: 0;
}
.np-pill {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 999px;
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--accent-dark);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow);
}
.np-pill:hover { background: var(--accent-soft); }
.np-pill svg { width: 1.1em; height: 1.1em; display: block; }
.np-pill.disabled { opacity: 0.4; pointer-events: none; }
.np-popup-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 50;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s ease;
}
.np-popup-backdrop.open { opacity: 1; pointer-events: auto; }
.np-popup {
  position: fixed;
  left: 50%;
  bottom: 0;
  transform: translate(-50%, 100%);
  width: 100%;
  max-width: 420px;
  z-index: 51;
  background: var(--card);
  border-radius: 18px 18px 0 0;
  padding-bottom: env(safe-area-inset-bottom, 0);
  box-shadow: 0 -8px 30px rgba(0, 0, 0, 0.28);
  transition: transform 0.32s var(--ease-sheet);
  pointer-events: none;
}
.np-popup.open { transform: translate(-50%, 0); pointer-events: auto; }
.np-popup-title {
  font-size: 0.8rem;
  opacity: 0.55;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 16px 20px 8px;
}
.np-popup-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: none;
  border: none;
  text-align: left;
  padding: 14px 20px;
  font-size: 1rem;
  color: var(--ink);
  cursor: pointer;
}
.np-popup-item:hover { background: var(--accent-soft); }
.np-popup-item.selected { color: var(--accent-dark); font-weight: 700; }
.np-popup-item .check { opacity: 0; }
.np-popup-item.selected .check { opacity: 1; }
.np-help-item {
  padding: 9px 20px;
  font-size: 0.92rem;
  line-height: 1.5;
  color: var(--ink);
}
.np-help-item strong { color: var(--accent-dark); }
.np-help-close {
  display: block;
  width: calc(100% - 40px);
  margin: 14px 20px 18px;
  padding: 12px;
  border-radius: 12px;
  border: none;
  background: var(--accent);
  color: #fff;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
}

/* Tactile press feedback on tappable controls */
.play-toggle, .np-play-btn, .np-side-btn, .np-pill, .dl-btn,
.theme-toggle, .expand-toggle, .np-popup-item, .np-help-close, .download-all-btn {
  transition: transform 0.12s ease, background 0.12s ease;
}
.play-toggle:active, .np-play-btn:active, .np-side-btn:active,
.np-pill:active:not(.disabled), .dl-btn:active, .theme-toggle:active,
.expand-toggle:active, .np-popup-item:active, .np-help-close:active,
.book-card:active, .tile:active, li.track:active, .podcast-link:active,
.download-all-btn:active {
  transform: scale(0.95);
}

/* Staggered entrance for grids/lists. Items start invisible (opacity: 0 here)
   and only animate in once JS (applyStagger in bindContent) has set a
   per-item animation-delay and added .stagger-in — this ordering, rather than
   auto-playing the animation on parse, is what makes the stagger actually
   stagger instead of every item animating with the same delay. */
.book-card, .tile, li.track { opacity: 0; }
.book-card.stagger-in, .tile.stagger-in, li.track.stagger-in {
  animation: stagger-in-kf 0.32s ease both;
}
@keyframes stagger-in-kf {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.skeleton {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--accent-dark);
}
.skeleton-ring {
  position: relative;
  width: 60px;
  height: 60px;
  margin-bottom: 18px;
}
.skeleton-ring::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  animation: skeleton-spin 1.6s linear infinite;
}
.skeleton-mantra {
  font-size: 1.15rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  margin-bottom: 4px;
}
.skeleton-text {
  font-size: 0.85rem;
  opacity: 0.55;
}
@keyframes skeleton-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .book-card, .tile, li.track { opacity: 1; }
  .book-card.stagger-in, .tile.stagger-in, li.track.stagger-in,
  .skeleton-ring::before,
  .now-playing-overlay, .player-shell, .np-popup, #content {
    animation: none !important;
    transition: none !important;
  }
}

@media (max-width: 600px) {
  .hero img { width: 130px; height: 130px; }
  .hero h1 { font-size: 1.7rem; }
  .topbar { padding: 10px 14px; }
  .container { padding: 16px 12px; }
  .tile-grid { grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 8px; }
  .book-grid { grid-template-columns: 1fr; }
  .now-label { font-size: 0.85rem; }
  .np-art { width: 68vw; height: 68vw; }
  .np-controls { gap: 24px; }
  .np-secondary { gap: 6px; padding: 0 12px 22px; }
  .np-pill { padding: 6px 10px; font-size: 0.72rem; }
}
"""


GLOBAL_SCRIPT = """
const ICON_PLAY = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
const ICON_PAUSE = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>';
const SKELETON_HTML = '<div class="skeleton"><div class="skeleton-ring"></div><div class="skeleton-mantra">हरी ॐ</div><div class="skeleton-text">थोडा वेळ थांबा…</div></div>';

const SPEED_PRESETS = [0.75, 1, 1.25, 1.5, 1.75, 2];
const DEV_DIGITS = ['०', '१', '२', '३', '४', '५', '६', '७', '८', '९'];

function toDevanagari(n) {
  return String(n).split('').map(c => (c >= '0' && c <= '9') ? DEV_DIGITS[+c] : c).join('');
}

function formatTime(sec) {
  if (!isFinite(sec) || sec < 0) sec = 0;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return m + ':' + String(s).padStart(2, '0');
}

const APP = {
  currentSrc: null,
  currentLabel: '',
  subtitle: '',
  playlist: null,
  currentIndex: -1,
  seeking: false,
  audio: null,
  speed: 1,
  sleepMode: 'episode',
  sleepEndAt: 0,
  lastSaveAt: 0,
  resumeTime: 0,
  init() {
    this.audio = document.getElementById('player');
    this.audio.addEventListener('timeupdate', () => this.updateProgress());
    this.audio.addEventListener('loadedmetadata', () => {
      this.updateDuration();
      if (this.resumeTime) {
        this.audio.currentTime = this.resumeTime;
        this.resumeTime = 0;
      }
    });
    this.audio.addEventListener('play', () => this.updatePlayIcon(true));
    this.audio.addEventListener('pause', () => { this.updatePlayIcon(false); this.savePlayback(); });
    this.audio.addEventListener('ended', () => this.onEnded());

    document.getElementById('mini-bar').addEventListener('click', (e) => {
      if (e.target.closest('.play-toggle')) return;
      this.openOverlay();
    });
    document.getElementById('play-toggle').addEventListener('click', (e) => {
      e.stopPropagation();
      this.togglePlay();
    });

    document.getElementById('np-collapse').addEventListener('click', () => this.closeOverlay());
    document.getElementById('np-playpause').addEventListener('click', () => this.togglePlay());
    document.getElementById('np-prev').addEventListener('click', () => this.playPrev());
    document.getElementById('np-next').addEventListener('click', () => this.playNext());
    document.getElementById('np-speed').addEventListener('click', () => this.openPopup('speed'));
    document.getElementById('np-sleep').addEventListener('click', () => this.openPopup('sleep'));
    document.getElementById('np-help').addEventListener('click', () => this.openPopup('help'));
    document.getElementById('help-close').addEventListener('click', () => this.closePopup());
    document.getElementById('popup-backdrop').addEventListener('click', () => this.closePopup());
    document.getElementById('speed-popup').addEventListener('click', (e) => {
      const item = e.target.closest('.np-popup-item');
      if (item) this.setSpeed(item.dataset.value);
    });
    document.getElementById('sleep-popup').addEventListener('click', (e) => {
      const item = e.target.closest('.np-popup-item');
      if (item) this.setSleepOption(item.dataset.value);
    });

    const seek = document.getElementById('np-seek');
    seek.addEventListener('input', () => {
      this.seeking = true;
      document.getElementById('np-current-time').textContent = formatTime(parseFloat(seek.value));
    });
    seek.addEventListener('change', () => {
      this.audio.currentTime = parseFloat(seek.value);
      this.seeking = false;
    });

    window.addEventListener('pagehide', () => this.savePlayback());

    this.initTheme();
    this.initSpeed();
    this.renderSleepLabel();
    this.initMediaSession();
    this.restorePlayback();
    bindContent();
  },
  play(src, label, opts) {
    opts = opts || {};
    if (this.currentSrc !== src) {
      this.audio.src = src;
      this.currentSrc = src;
      this.currentLabel = label;
      document.getElementById('now-label').textContent = label;
      document.getElementById('np-title').textContent = label;
      this.audio.playbackRate = this.speed;
      this.updateDownloadLink(src);
    }
    if (opts.subtitle !== undefined) {
      this.subtitle = opts.subtitle;
      document.getElementById('np-subtitle').textContent = opts.subtitle;
    }
    if (opts.playlist !== undefined) {
      this.playlist = opts.playlist;
      this.currentIndex = opts.index;
    }
    this.audio.play();
    document.getElementById('player-shell').classList.add('active');
    this.updateNavButtons();
    this.refreshHighlight();
    this.updateMediaSessionMetadata();
    this.savePlayback();
  },
  togglePlay() {
    if (!this.currentSrc) return;
    if (this.audio.paused) this.audio.play(); else this.audio.pause();
  },
  playPrev() {
    if (!this.playlist || this.currentIndex <= 0) return;
    const item = this.playlist[this.currentIndex - 1];
    this.play(item.src, item.label, { subtitle: this.subtitle, playlist: this.playlist, index: this.currentIndex - 1 });
  },
  playNext() {
    if (!this.playlist || this.currentIndex >= this.playlist.length - 1) return;
    const item = this.playlist[this.currentIndex + 1];
    this.play(item.src, item.label, { subtitle: this.subtitle, playlist: this.playlist, index: this.currentIndex + 1 });
  },
  updateNavButtons() {
    const hasPrev = !!this.playlist && this.currentIndex > 0;
    const hasNext = !!this.playlist && this.currentIndex < this.playlist.length - 1;
    document.getElementById('np-prev').disabled = !hasPrev;
    document.getElementById('np-next').disabled = !hasNext;
  },
  refreshHighlight() {
    document.querySelectorAll('#content .track').forEach(el => {
      el.classList.toggle('playing', el.getAttribute('data-src') === this.currentSrc);
    });
  },
  openOverlay() {
    if (!this.currentSrc) return;
    document.getElementById('now-playing-overlay').classList.add('open');
  },
  closeOverlay() {
    document.getElementById('now-playing-overlay').classList.remove('open');
  },
  updatePlayIcon(playing) {
    const icon = playing ? ICON_PAUSE : ICON_PLAY;
    document.getElementById('play-toggle').innerHTML = icon;
    document.getElementById('np-playpause').innerHTML = icon;
    if ('mediaSession' in navigator) {
      navigator.mediaSession.playbackState = playing ? 'playing' : 'paused';
    }
  },
  updateProgress() {
    if (!this.audio.duration) return;
    const pct = (this.audio.currentTime / this.audio.duration) * 100;
    document.getElementById('progress-fill').style.width = pct + '%';
    if (!this.seeking) {
      document.getElementById('np-seek').value = this.audio.currentTime;
      document.getElementById('np-current-time').textContent = formatTime(this.audio.currentTime);
    }
    if ('mediaSession' in navigator && 'setPositionState' in navigator.mediaSession) {
      navigator.mediaSession.setPositionState({
        duration: this.audio.duration,
        playbackRate: this.audio.playbackRate,
        position: this.audio.currentTime,
      });
    }
    if (Date.now() - this.lastSaveAt > 5000) this.savePlayback();
    this.checkSleepTimer();
  },
  updateDuration() {
    document.getElementById('np-seek').max = this.audio.duration || 0;
    document.getElementById('np-duration').textContent = formatTime(this.audio.duration);
  },
  initTheme() {
    const btn = document.getElementById('theme-toggle');
    const saved = localStorage.getItem('theme');
    const preferred = saved || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    this.applyTheme(preferred);
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      this.applyTheme(current === 'dark' ? 'light' : 'dark');
    });
  },
  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    document.getElementById('theme-toggle').textContent = theme === 'dark' ? '☀' : '🌙';
  },
  initSpeed() {
    const saved = parseFloat(localStorage.getItem('ak_speed'));
    this.speed = SPEED_PRESETS.includes(saved) ? saved : 1;
    this.audio.playbackRate = this.speed;
    this.renderSpeedLabel();
  },
  renderSpeedLabel() {
    document.getElementById('np-speed').textContent = 'गती ' + this.speed + '×';
  },
  setSpeed(value) {
    this.speed = Number(value);
    this.audio.playbackRate = this.speed;
    localStorage.setItem('ak_speed', this.speed);
    this.renderSpeedLabel();
    this.closePopup();
  },
  setSleepOption(value) {
    if (value === 'off') {
      this.sleepMode = null;
      this.sleepEndAt = 0;
    } else if (value === 'episode') {
      this.sleepMode = 'episode';
      this.sleepEndAt = 0;
    } else {
      const minutes = Number(value);
      this.sleepMode = minutes;
      this.sleepEndAt = Date.now() + minutes * 60000;
    }
    this._lastSleepLabelMin = null;
    this.renderSleepLabel();
    this.closePopup();
  },
  checkSleepTimer() {
    if (typeof this.sleepMode !== 'number' || !this.sleepEndAt) return;
    const remainingMs = this.sleepEndAt - Date.now();
    if (remainingMs <= 0) {
      this.audio.pause();
      this.sleepMode = null;
      this.sleepEndAt = 0;
      this.renderSleepLabel();
      return;
    }
    const remainingMin = Math.ceil(remainingMs / 60000);
    if (remainingMin !== this._lastSleepLabelMin) {
      this._lastSleepLabelMin = remainingMin;
      document.getElementById('np-sleep').textContent = toDevanagari(remainingMin) + ' मि';
    }
  },
  renderSleepLabel() {
    const btn = document.getElementById('np-sleep');
    if (this.sleepMode === 'episode') {
      btn.textContent = 'भाग अखेर';
    } else if (typeof this.sleepMode === 'number') {
      btn.textContent = toDevanagari(this.sleepMode) + ' मि';
    } else {
      btn.textContent = 'टायमर';
    }
  },
  onEnded() {
    this.updatePlayIcon(false);
    this.audio.currentTime = 0;
    if (this.sleepMode === 'episode') {
      this.sleepMode = null;
      this.renderSleepLabel();
      return;
    }
    this.playNext();
  },
  openPopup(name) {
    ['speed', 'sleep', 'help'].forEach(n => {
      document.getElementById(n + '-popup').classList.toggle('open', n === name);
    });
    document.getElementById('popup-backdrop').classList.add('open');
    if (name === 'speed' || name === 'sleep') {
      const popup = document.getElementById(name + '-popup');
      const selected = name === 'speed' ? String(this.speed) : (this.sleepMode === null ? 'off' : String(this.sleepMode));
      popup.querySelectorAll('.np-popup-item').forEach(item => {
        item.classList.toggle('selected', item.dataset.value === selected);
      });
    }
  },
  closePopup() {
    document.getElementById('popup-backdrop').classList.remove('open');
    ['speed', 'sleep', 'help'].forEach(n => document.getElementById(n + '-popup').classList.remove('open'));
  },
  updateDownloadLink(src) {
    const btn = document.getElementById('np-download');
    const filename = decodeURIComponent(src.split('/').pop());
    btn.href = src;
    btn.setAttribute('download', filename);
    btn.classList.remove('disabled');
  },
  initMediaSession() {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.setActionHandler('play', () => this.audio.play());
    navigator.mediaSession.setActionHandler('pause', () => this.audio.pause());
    navigator.mediaSession.setActionHandler('previoustrack', () => this.playPrev());
    navigator.mediaSession.setActionHandler('nexttrack', () => this.playNext());
    navigator.mediaSession.setActionHandler('seekbackward', (details) => {
      this.audio.currentTime = Math.max(0, this.audio.currentTime - (details.seekOffset || 10));
    });
    navigator.mediaSession.setActionHandler('seekforward', (details) => {
      this.audio.currentTime = Math.min(this.audio.duration || Infinity, this.audio.currentTime + (details.seekOffset || 10));
    });
    navigator.mediaSession.setActionHandler('seekto', (details) => {
      if (details.seekTime !== undefined) this.audio.currentTime = details.seekTime;
    });
  },
  updateMediaSessionMetadata() {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: this.currentLabel,
      artist: 'अमृतकण',
      album: this.subtitle || '',
      artwork: [
        { src: '/static/mauli.jpg?v=2', sizes: '512x512', type: 'image/jpeg' },
      ],
    });
  },
  savePlayback() {
    if (!this.currentSrc) return;
    this.lastSaveAt = Date.now();
    localStorage.setItem('ak_playback', JSON.stringify({
      src: this.currentSrc,
      label: this.currentLabel,
      subtitle: this.subtitle,
      playlist: this.playlist,
      index: this.currentIndex,
      currentTime: this.audio.currentTime,
    }));
  },
  restorePlayback() {
    let saved;
    try {
      saved = JSON.parse(localStorage.getItem('ak_playback') || 'null');
    } catch (e) {
      saved = null;
    }
    if (!saved || !saved.src) return;
    this.audio.src = saved.src;
    this.audio.playbackRate = this.speed;
    this.currentSrc = saved.src;
    this.currentLabel = saved.label || '';
    this.subtitle = saved.subtitle || '';
    this.playlist = saved.playlist || null;
    this.currentIndex = typeof saved.index === 'number' ? saved.index : -1;
    this.resumeTime = saved.currentTime || 0;
    document.getElementById('now-label').textContent = this.currentLabel;
    document.getElementById('np-title').textContent = this.currentLabel;
    document.getElementById('np-subtitle').textContent = this.subtitle;
    document.getElementById('player-shell').classList.add('active');
    this.updateDownloadLink(saved.src);
    this.updateNavButtons();
    this.refreshHighlight();
    this.updateMediaSessionMetadata();
  }
};

function bindContent() {
  const search = document.getElementById('search');
  const container = document.querySelector('#content .episode-list');
  const list = document.querySelectorAll('#content .track');
  let subtitle = '';
  if (container) {
    const book = container.dataset.book || '';
    const chapter = container.dataset.chapter || '';
    subtitle = chapter ? (book + ' · ' + chapter) : book;
  }
  const playlist = [...list].map(el => ({ src: el.getAttribute('data-src'), label: el.textContent }));
  if (search) {
    search.addEventListener('input', e => {
      const q = e.target.value.toLowerCase();
      list.forEach(el => {
        el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
      updateCount(list);
    });
  }
  list.forEach((el, idx) => {
    el.addEventListener('click', (e) => {
      if (e.target.closest('.dl-btn')) return;
      APP.play(el.getAttribute('data-src'), el.textContent, { subtitle, playlist, index: idx });
    });
  });
  APP.refreshHighlight();
  updateCount(list);
  applyStagger(document.querySelectorAll('#content .book-card, #content .tile, #content .track'));
}

function applyStagger(elements) {
  elements.forEach((el, i) => {
    el.style.animationDelay = (Math.min(i, 10) * 28) + 'ms';
    el.classList.add('stagger-in');
  });
}

function updateCount(list) {
  const countEl = document.getElementById('count');
  if (!countEl) return;
  const visible = [...list].filter(el => el.style.display !== 'none').length;
  countEl.textContent = visible + ' / ' + list.length + ' भाग';
}

function isInternalLink(a) {
  return a.origin === location.origin;
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function navigateTo(path, push) {
  const content = document.getElementById('content');
  content.classList.add('fading');
  await sleep(140);
  content.innerHTML = SKELETON_HTML;
  content.classList.remove('fading');
  try {
    const res = await fetch(path, { headers: { 'X-Partial': '1' } });
    if (!res.ok) { location.href = path; return; }
    const text = await res.text();
    content.classList.add('fading');
    await sleep(140);
    content.innerHTML = text;
    if (push) history.pushState({ path }, '', path);
    window.scrollTo(0, 0);
    content.classList.remove('fading');
    bindContent();
  } catch (err) {
    location.href = path;
  }
}

document.addEventListener('click', (e) => {
  const a = e.target.closest('a');
  if (!a || !isInternalLink(a) || a.target === '_blank' || a.hasAttribute('download')) return;
  e.preventDefault();
  navigateTo(a.pathname, true);
});

window.addEventListener('popstate', () => {
  navigateTo(location.pathname, false);
});

document.addEventListener('DOMContentLoaded', () => APP.init());
"""


ICON_PLAY = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>'
ICON_PAUSE = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h4v14H6zM14 5h4v14h-4z"/></svg>'
ICON_SKIP_PREV = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 5h2v14H6zM20 5v14l-11-7z"/></svg>'
ICON_SKIP_NEXT = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M4 5v14l11-7zM16 5h2v14h-2z"/></svg>'
ICON_DOWNLOAD = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M11 3h2v10h-2z"/><path d="M7 11h10l-5 6z"/><path d="M4 19h16v2H4z"/></svg>'
ICON_HELP = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="7.5" r="1.3" fill="currentColor"/><rect x="10.8" y="10.5" width="2.4" height="7" rx="1.2" fill="currentColor"/></svg>'
ICON_FOLDER = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 5a1 1 0 0 1 1-1h5l1.7 1.7H20a1 1 0 0 1 1 1V18a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/></svg>'
ICON_TRACK = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3z"/></svg>'

SITE_DESCRIPTION = "ज्ञानेश्वरी आणि इतर मराठी ग्रंथांचं निरूपण — ध्वनिरूपात ऐका"

GA_MEASUREMENT_ID = "G-KLHSC2QRRW"
GA_SNIPPET = f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_MEASUREMENT_ID}');
</script>"""


def page_shell(title, body_html, base_url=""):
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
<style>{BASE_CSS}</style>
{GA_SNIPPET}
</head>
<body>
<div class="topbar">
  <a href="/" class="topbar-link">
    <img src="/static/mauli.jpg?v=2" alt="Dnyaneshwar Mauli">
    <span class="site-title">अमृतकण</span>
  </a>
  <button id="theme-toggle" class="theme-toggle" aria-label="Toggle dark mode">🌙</button>
</div>
<div class="container">
<div id="content">
{body_html}
</div>
</div>
<div id="player-shell" class="player-shell">
  <div id="mini-bar" class="mini-bar">
    <button id="play-toggle" class="play-toggle" aria-label="Play or pause">{ICON_PLAY}</button>
    <div class="mini-info">
      <div id="now-label" class="now-label">काहीही निवडलेले नाही</div>
      <div class="progress-track"><div id="progress-fill" class="progress-fill"></div></div>
    </div>
    <button id="expand-toggle" class="expand-toggle" aria-label="Expand player">⌃</button>
  </div>
</div>
<audio id="player" preload="metadata"></audio>
<div id="now-playing-overlay" class="now-playing-overlay">
  <div class="np-header">
    <button id="np-collapse" class="np-collapse" aria-label="Collapse player">⌄</button>
    <div class="np-header-title">आता वाजत आहे</div>
    <div class="np-header-spacer"></div>
  </div>
  <div class="np-art-wrap">
    <img src="/static/mauli.jpg?v=2" class="np-art" alt="">
  </div>
  <div class="np-meta">
    <div id="np-title" class="np-title"></div>
    <div id="np-subtitle" class="np-subtitle"></div>
  </div>
  <div class="np-progress">
    <input id="np-seek" class="np-seek" type="range" min="0" max="0" value="0" step="0.1">
    <div class="np-time-row">
      <span id="np-current-time">0:00</span>
      <span id="np-duration">0:00</span>
    </div>
  </div>
  <div class="np-controls">
    <button id="np-prev" class="np-side-btn" aria-label="Previous track">{ICON_SKIP_PREV}</button>
    <button id="np-playpause" class="np-play-btn" aria-label="Play or pause">{ICON_PLAY}</button>
    <button id="np-next" class="np-side-btn" aria-label="Next track">{ICON_SKIP_NEXT}</button>
  </div>
  <div class="np-secondary">
    <button id="np-speed" class="np-pill" aria-label="गती">गती 1×</button>
    <button id="np-sleep" class="np-pill" aria-label="टायमर">भाग अखेर</button>
    <a id="np-download" class="np-pill disabled" aria-label="डाउनलोड करा" download>{ICON_DOWNLOAD} डाउनलोड</a>
    <button id="np-help" class="np-pill" aria-label="मदत" title="मदत">{ICON_HELP}</button>
  </div>
</div>
<div id="popup-backdrop" class="np-popup-backdrop"></div>
<div id="speed-popup" class="np-popup">
  <div class="np-popup-title">गती</div>
  <button class="np-popup-item" data-value="0.75">0.75× <span class="check">✓</span></button>
  <button class="np-popup-item" data-value="1">1× <span class="check">✓</span></button>
  <button class="np-popup-item" data-value="1.25">1.25× <span class="check">✓</span></button>
  <button class="np-popup-item" data-value="1.5">1.5× <span class="check">✓</span></button>
  <button class="np-popup-item" data-value="1.75">1.75× <span class="check">✓</span></button>
  <button class="np-popup-item" data-value="2">2× <span class="check">✓</span></button>
</div>
<div id="sleep-popup" class="np-popup">
  <div class="np-popup-title">टायमर</div>
  <button class="np-popup-item" data-value="episode">भाग संपल्यावर <span class="check">✓</span></button>
  <button class="np-popup-item" data-value="15">१५ मिनिटे <span class="check">✓</span></button>
  <button class="np-popup-item" data-value="30">३० मिनिटे <span class="check">✓</span></button>
  <button class="np-popup-item" data-value="45">४५ मिनिटे <span class="check">✓</span></button>
  <button class="np-popup-item" data-value="60">६० मिनिटे <span class="check">✓</span></button>
  <button class="np-popup-item" data-value="off">बंद <span class="check">✓</span></button>
</div>
<div id="help-popup" class="np-popup">
  <div class="np-popup-title">मदत</div>
  <div class="np-help-item"><strong>गती</strong> — निरूपणाची गती</div>
  <div class="np-help-item"><strong>टायमर</strong> — निरूपण बंद करायचा टायमर</div>
  <div class="np-help-item"><strong>डाउनलोड</strong> — भाग डाउनलोड करा</div>
  <button id="help-close" class="np-help-close">ठीक आहे</button>
</div>
<script>{GLOBAL_SCRIPT}</script>
</body>
</html>"""


MOBILE_UA_RE = re.compile(r"iphone|ipad|ipod|android", re.IGNORECASE)


def render_home_main(is_mobile):
    body = ['<div class="section-card">', '<div class="hero">']
    body.append('<img src="/static/mauli.jpg?v=2" alt="श्री ज्ञानेश्वर माऊली">')
    body.append('<h1>अमृतकण</h1>')
    body.append('<p class="tagline">ज्ञानेश्वरी आणि इतर मराठी ग्रंथांचं निरूपण</p>')
    body.append('</div>')
    body.append('<div class="book-grid">')
    for book in BOOK_DEFS:
        lib = LIBRARY[book["id"]]
        total = sum(len(v) for v in lib["chapters"].values())
        body.append(f"""
<a class="book-card" href="/book/{book['id']}">
  <h2>{html.escape(book['name'])}</h2>
  <div class="count">{to_devanagari(total)} भाग</div>
</a>""")
    body.append('</div>')
    if PODCAST_LINKS:
        body.append('<div class="podcast-footer">')
        body.append('<div class="podcast-footer-title">निरूपण इथेही उपलब्ध</div>')
        body.append('<div class="podcast-links">')
        # On mobile, skip target="_blank": opening in a new tab unreliably
        # suppresses iOS/Android's native-app handoff (Universal/App Links) for
        # these official podcast domains, so a same-tab link is what lets the
        # OS open the installed Spotify/Podcasts/Amazon Music app instead.
        link_attrs = '' if is_mobile else ' target="_blank" rel="noopener noreferrer"'
        for link in PODCAST_LINKS:
            body.append(f"""
<a class="podcast-link" href="{html.escape(link['url'])}"{link_attrs}>
  <span class="podcast-icon">
    <svg viewBox="0 0 24 24" fill="{link['color']}"><path d="{link['path']}"/></svg>
  </span>
  <span>{html.escape(link['label'])}</span>
</a>""")
        body.append('</div>')
        body.append('</div>')
    body.append('</div>')
    return "\n".join(body)


def render_home_youtube():
    body = ['<div class="section-card">']
    body.append('<h2 class="section-title">यूट्यूब चॅनल</h2>')
    body.append('<p class="section-lead">अमृतकणचे व्हिडिओ यूट्यूबवर पहा</p>')
    body.append(f"""
<a class="yt-channel-link" href="{html.escape(YOUTUBE_CHANNEL_URL)}" target="_blank" rel="noopener noreferrer">
  <svg viewBox="0 0 24 24" fill="{YOUTUBE_ICON_COLOR}"><path d="{YOUTUBE_ICON_PATH}"/></svg>
  <span>{html.escape(YOUTUBE_CHANNEL_HANDLE)} चॅनलला भेट द्या</span>
</a>""")
    body.append('<div class="yt-video-grid">')
    for video_id in YOUTUBE_VIDEO_IDS:
        embed_url = f"https://www.youtube-nocookie.com/embed/{urllib.parse.quote(video_id)}"
        body.append(f"""
<iframe class="yt-embed" src="{embed_url}" title="अमृतकण यूट्यूब व्हिडिओ"
  loading="lazy" allowfullscreen
  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>""")
    body.append('</div>')
    body.append('</div>')
    return "\n".join(body)


def render_home_about():
    return f"""
<div class="section-card">
  <h2 class="section-title">आमच्याबद्दल</h2>
  <p class="about-text">{html.escape(ABOUT_TEXT_MR)}</p>
  <div class="about-me">
    <h3 class="about-me-title">माझ्याबद्दल</h3>
    <div class="about-me-row">
      <img class="about-me-photo" src="/static/sk_chaudhari.jpg" alt="Dr Suresh Kumar Chaudhari">
      <div class="about-me-text"></div>
    </div>
  </div>
</div>"""


def render_home(is_mobile=False):
    sections = [render_home_main(is_mobile), render_home_youtube(), render_home_about()]
    body = '<div class="home-scroll">\n' + "\n".join(
        f'<section class="home-section">{s}</section>' for s in sections
    ) + '\n</div>'
    return "अमृतकण", body


SPECIAL_CHAPTER_LABELS = {
    key: label
    for special in SPECIAL_CHAPTER_ORDER.values()
    for label, key in special["lead"] + special["trail"]
}


def render_book(book_id):
    if book_id not in LIBRARY:
        raise LookupError(book_id)
    lib = LIBRARY[book_id]
    body = [f"""<div class="breadcrumb"><a href="/">अमृतकण</a> / {html.escape(lib['name'])}</div>"""]
    body.append(f"<h1 class=\"page-title\">{html.escape(lib['name'])}</h1>")
    body.append(f"""
<div class="page-actions">
  <a class="download-all-btn" href="/download/book/{book_id}" download="{html.escape(book_id)}.zip">{ICON_DOWNLOAD} संपूर्ण ग्रंथ डाउनलोड करा (ZIP)</a>
</div>""")
    body.append('<div class="tile-grid">')
    for key in lib["order"]:
        count = len(lib["chapters"][key])
        if key == "other":
            slug = "other"
            label = "इतर"
            cls = "tile other"
        elif key in SPECIAL_CHAPTER_LABELS:
            slug = key
            label = SPECIAL_CHAPTER_LABELS[key]
            cls = "tile other"
        else:
            slug = str(key)
            label = f"{lib['unit']} {to_devanagari(key)}"
            cls = "tile"
        icon = ICON_TRACK if count == 1 else ICON_FOLDER
        badge = "" if count == 1 else f'<div class="badge">{to_devanagari(count)} भाग</div>'
        body.append(f"""
<a class="{cls}" href="/book/{book_id}/{slug}">
  <div class="tile-icon">{icon}</div>
  <div class="num">{html.escape(label)}</div>
  {badge}
</a>""")
    body.append('</div>')
    return lib["name"], "\n".join(body)


def render_chapter(book_id, slug):
    if book_id not in LIBRARY:
        raise LookupError(book_id)
    lib = LIBRARY[book_id]
    if slug == "other":
        key = "other"
        chapter_label = "इतर"
    elif slug in SPECIAL_CHAPTER_LABELS:
        key = slug
        chapter_label = SPECIAL_CHAPTER_LABELS[slug]
    else:
        try:
            key = int(slug)
        except ValueError:
            raise LookupError(slug)
        chapter_label = f"{lib['unit']} {to_devanagari(key)}"
    if key not in lib["chapters"]:
        raise LookupError(slug)

    items = lib["chapters"][key]
    body = [f"""<div class="breadcrumb"><a href="/">अमृतकण</a> / <a href="/book/{book_id}">{html.escape(lib['name'])}</a> / {html.escape(chapter_label)}</div>"""]
    body.append(f"<h1 class=\"page-title\">{html.escape(chapter_label)}</h1>")
    body.append(f"""
<div class="page-actions">
  <a class="download-all-btn" href="/download/book/{book_id}/{slug}" download="{html.escape(book_id)}-{html.escape(slug)}.zip">{ICON_DOWNLOAD} संपूर्ण {html.escape(chapter_label)} डाउनलोड करा (ZIP)</a>
</div>""")
    body.append(f"""
<input id="search" placeholder="शोधा...">
<div id="count"></div>
<ul class="episode-list" id="filelist" data-book="{html.escape(lib['name'])}" data-chapter="{html.escape(chapter_label)}">""")
    for filename, label in items:
        src = urllib.parse.quote(filename)
        body.append(f"""
<li class="track" data-src="/audio/{src}">
  <span class="track-label">{html.escape(label)}</span>
  <a class="dl-btn" href="/audio/{src}" download="{html.escape(filename)}" aria-label="डाउनलोड करा" title="डाउनलोड करा">{ICON_DOWNLOAD}</a>
</li>""")
    body.append("</ul>")
    return f"{chapter_label} - {lib['name']}", "\n".join(body)


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
    for the React web frontend — mirrors render_home_main/_youtube/_about."""
    return {
        "tagline": "ज्ञानेश्वरी आणि इतर मराठी ग्रंथांचं निरूपण",
        "siteDescription": SITE_DESCRIPTION,
        "heroImage": "/static/mauli.jpg?v=2",
        "aboutText": ABOUT_TEXT_MR,
        "aboutMePhoto": "/static/sk_chaudhari.jpg",
        "aboutMeText": "",
        "podcastLinks": PODCAST_LINKS,
        "youtube": {
            "channelUrl": YOUTUBE_CHANNEL_URL,
            "channelHandle": YOUTUBE_CHANNEL_HANDLE,
            "videoIds": YOUTUBE_VIDEO_IDS,
        },
    }


def api_library():
    """Full library tree as JSON, for native clients (e.g. the Android/iOS
    app) that can't scrape the server-rendered HTML the web frontend uses.
    Mirrors the same key/order/label logic as render_book/render_chapter."""
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
                is_mobile = bool(MOBILE_UA_RE.search(self.headers.get("User-Agent", "")))
                self.serve_page(render_home(is_mobile))
            elif parts[0] == "static" and len(parts) == 2:
                self.serve_static(parts[1])
            elif parts[0] == "audio" and len(parts) == 2:
                self.serve_audio(parts[1])
            elif parts[0] == "api" and len(parts) == 2 and parts[1] == "library":
                self.serve_json(api_library())
            elif parts[0] == "api" and len(parts) == 2 and parts[1] == "home":
                self.serve_json(api_home())
            elif parts[0] == "download" and len(parts) == 3 and parts[1] == "book":
                display_name, items = build_book_zip_items(parts[2])
                self.serve_zip(f"{parts[2]}.zip", f"{display_name}.zip", items)
            elif parts[0] == "download" and len(parts) == 4 and parts[1] == "book":
                display_name, items = build_chapter_zip_items(parts[2], parts[3])
                self.serve_zip(f"{parts[2]}-{parts[3]}.zip", f"{display_name}.zip", items)
            elif parts[0] == "book" and len(parts) == 2:
                self.serve_page(render_book(parts[1]))
            elif parts[0] == "book" and len(parts) == 3:
                self.serve_page(render_chapter(parts[1], parts[2]))
            else:
                self.send_error(404)
        except LookupError:
            self.send_error(404)

    def serve_page(self, title_and_body):
        title, body_html = title_and_body
        if self.headers.get("X-Partial"):
            self.serve_html(body_html)
        else:
            host = self.headers.get("Host", "")
            base_url = ""
            if host:
                scheme = "http" if host.startswith("localhost") or host.startswith("127.") else "https"
                base_url = f"{scheme}://{host}"
            self.serve_html(page_shell(title, body_html, base_url))

    def serve_html(self, body_str):
        body = body_str.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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

    def serve_zip(self, ascii_name, display_name, items):
        """Streams a ZIP of the given (arcname, filepath) pairs directly to
        the client, uncompressed (ZIP_STORED - the mp3/m4a sources are already
        compressed, so re-compressing would only cost CPU for no size win).
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
        access_logger.info(
            "%s [%s] %s",
            self.client_address[0],
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
