import streamlit as st
import zipfile
import io
import re
from datetime import timedelta

# Templates pour le manifest SCORM 1.2 et SCORM 2004
MANIFEST_12 = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="com.example.scorm" version="1.0"
          xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2
          imscp_rootv1p1p2.xsd">
  <organizations default="ORG">
    <organization identifier="ORG">
      <title>SCORM Module</title>
      <item identifier="ITEM" identifierref="RES">
        <title>SCORM URL Content</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES" type="webcontent" adlcp:scormtype="sco" href="index.html">
      <file href="index.html"/>
      <file href="scorm.js"/>
    </resource>
  </resources>
</manifest>'''

MANIFEST_2004 = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="com.example.scorm" version="1.0"
          xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 imscp_v1p1.xsd">
  <organizations default="ORG">
    <organization identifier="ORG">
      <title>SCORM Module</title>
      <item identifier="ITEM" identifierref="RES">
        <title>SCORM URL Content</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES" type="webcontent" adlcp:scormType="sco" href="index.html">
      <file href="index.html"/>
      <file href="scorm.js"/>
    </resource>
  </resources>
</manifest>'''

HTML_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
  <title>SCORM Content</title>
  <script src="scorm.js"></script>
  <script>
    let elapsed = 0;
    const requiredTime = {time};

    window.onload = function() {
      pipwerks.SCORM.version = "1.2";
      pipwerks.SCORM.init();

      document.getElementById("target").src = "{url}";

      const timer = setInterval(() => {
        elapsed++;
        const progress = Math.min((elapsed / requiredTime) * 100, 100);

        pipwerks.SCORM.set("cmi.core.score.raw", progress.toFixed(0));
        pipwerks.SCORM.set("cmi.core.lesson_location", elapsed.toString());

        if (elapsed >= requiredTime) {
          pipwerks.SCORM.set("cmi.core.lesson_status", "completed");
          clearInterval(timer);
          pipwerks.SCORM.quit();
        } else {
          pipwerks.SCORM.set("cmi.core.lesson_status", "incomplete");
        }

        pipwerks.SCORM.save();
      }, 1000);
    }
  </script>
</head>
<body>
  <h2>Chargement du contenu...</h2>
  <iframe id="target" width="100%" height="600px" style="border: none;"></iframe>
</body>
</html>'''

SCORM_JS = '''// pipwerks SCORM API Wrapper (simplifié pour SCORM 1.2)
var pipwerks = {
  SCORM: {
    version: "1.2",
    handleCompletion: true,
    api: null,

    init: function() {
      this.api = this.getAPIHandle();
      if (this.api === null) {
        console.error("SCORM API non trouvée.");
        return false;
      }
      return this.api.LMSInitialize("") === "true";
    },

    get: function(parameter) {
      return this.api ? this.api.LMSGetValue(parameter) : null;
    },

    set: function(parameter, value) {
      return this.api ? this.api.LMSSetValue(parameter, value) === "true" : false;
    },

    save: function() {
      return this.api ? this.api.LMSCommit("") === "true" : false;
    },

    quit: function() {
      return this.api ? this.api.LMSFinish("") === "true" : false;
    },

    getAPIHandle: function() {
      var win = window;
      while (win) {
        if (win.API) return win.API;
        if (win.parent && win.parent !== win) win = win.parent;
        else break;
      }
      return null;
    }
  }
};'''

def parse_duration_to_seconds(duration_str):
    duration_str = duration_str.replace(" ", "")
    pattern = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$")
    match = pattern.match(duration_str)

    if not match:
        return None, "Le format de durée doit être HH:MM:SS (ex: 00:01:30 ou 25:01:30)."

    try:
        h, m, s = map(int, match.groups())
    except ValueError:
        return None, "Les valeurs de durée ne sont pas valides (doivent être des nombres)."

    if not (0 <= m <= 59 and 0 <= s <= 59):
        return None, "Les minutes (00-59) et les secondes (00-59) ne sont pas valides."

    total_seconds = (h * 3600) + (m * 60) + s
    if total_seconds == 0:
        return None, "La durée totale doit être supérieure à zéro."

    return total_seconds, None

# --- Streamlit App ---
st.title("Générateur de paquet SCORM")

predefined_urls = {
    "Exemple Google": "https://www.google.com",
    "Exemple Wikipédia": "https://fr.wikipedia.org/wiki/Wikipédia",
    "Exemple OpenAI": "https://openai.com",
    "Autre (saisir ci-dessous)": ""
}

selected_predefined_url_name = st.selectbox(
    "Choisir une URL prédéfinie :",
    list(predefined_urls.keys())
)

default_url_value = predefined_urls[selected_predefined_url_name]

url = st.text_input("URL à consulter (modifiable) :", value=default_url_value)

scorm_version = st.selectbox("Version SCORM", ["SCORM 1.2", "SCORM 2004 3rd edition"])

st.subheader("Durée minimale de consultation")
duration_input = st.text_input("Durée (HH:MM:SS) :", value="00:00:30")

if st.button("Générer le SCORM"):
    if not url.strip():
        st.error("Veuillez saisir une URL à consulter.")
    else:
        total_duration_in_seconds, error_message = parse_duration_to_seconds(duration_input)

        if error_message:
            st.error(error_message)
        else:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                html_content = HTML_TEMPLATE.replace("{url}", url).replace("{time}", str(total_duration_in_seconds))
                zf.writestr("index.html", html_content)
                zf.writestr("scorm.js", SCORM_JS)

                if scorm_version == "SCORM 1.2":
                    zf.writestr("imsmanifest.xml", MANIFEST_12)
                else:
                    zf.writestr("imsmanifest.xml", MANIFEST_2004)

            st.success("Fichier SCORM généré !")
            st.download_button(
                "📥 Télécharger le paquet SCORM",
                data=buffer.getvalue(),
                file_name="scorm_package.zip",
                mime="application/zip"
            )
