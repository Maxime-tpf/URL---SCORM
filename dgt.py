import streamlit as st
import zipfile
import io
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
</manifest>
'''

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
</manifest>
'''

# HTML + JS avec minuterie et pipwerks SCORM wrapper amélioré
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
  <iframe id="target" width="100%" height="600px"></iframe>
</body>
</html>
'''

# pipwerks SCORM wrapper JS minimal (version 1.2)
SCORM_JS = '''// pipwerks SCORM API Wrapper (simplifié)
var pipwerks = {
  SCORM: {
    version: "1.2",
    handleCompletion: true,
    api: null,
    init: function() {
      this.api = this.getAPIHandle();
      if (this.api === null) return false;
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
};
'''

# --- Streamlit App ---
st.title("Générateur de paquet SCORM")

url = st.text_input("URL à consulter", "https://example.com")
scorm_version = st.selectbox("Version SCORM", ["SCORM 1.2", "SCORM 2004 3rd edition"])

# Sélection d'heure / minute / seconde pour la durée
st.write("### Durée minimale requise avant validation")
heures = st.selectbox("Heures", list(range(0, 6)), index=0)
minutes = st.selectbox("Minutes", list(range(0, 60)), index=0)
secondes = st.selectbox("Secondes", list(range(0, 60)), index=30)

# Calcul de la durée en secondes
duration = heures * 3600 + minutes * 60 + secondes

if st.button("Générer le SCORM"):
    # Créer un zip en mémoire
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        html_content = HTML_TEMPLATE.replace("{url}", url).replace("{time}", str(duration))
        zf.writestr("index.html", html_content)
        zf.writestr("scorm.js", SCORM_JS)

        if scorm_version == "SCORM 1.2":
            zf.writestr("imsmanifest.xml", MANIFEST_12)
        else:
            zf.writestr("imsmanifest.xml", MANIFEST_2004)

    st.success("Fichier SCORM généré !")
    st.download_button("📥 Télécharger le paquet SCORM", data=buffer.getvalue(), file_name="scorm_package.zip")

