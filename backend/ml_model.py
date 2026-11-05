"""
The 'brain' of Fineprint: a small NLP clause classifier.

TF-IDF (word 1-2 grams) + Logistic Regression (scikit-learn), plus a few
hand-written rules on top (hybrid ML + rules), and negation handling so that
"We do NOT sell your data" is not flagged as a data-selling clause.

Upgrade path: swap `classify_sentences` for a zero-shot Hugging Face pipeline
(facebook/bart-large-mnli) or a fine-tuned BERT model - the rest of the app
does not need to change.
"""
import os
import re

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .training_data import TRAINING

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

# weight = points deducted from the privacy score (negative = bonus)
LABELS = {
    "data_selling": {"name": "Data selling", "risk": "high", "weight": 14,
                     "plain": "They may sell or trade your personal data."},
    "sensitive_data": {"name": "Sensitive data", "risk": "high", "weight": 10,
                       "plain": "They collect sensitive data like precise location, biometrics, contacts or health details."},
    "third_party_sharing": {"name": "Third-party sharing", "risk": "medium", "weight": 7,
                            "plain": "Your data can be passed on to partners, advertisers or affiliates."},
    "tracking_profiling": {"name": "Tracking & profiling", "risk": "medium", "weight": 6,
                           "plain": "They follow your activity and build a profile of your interests."},
    "long_retention": {"name": "Long retention", "risk": "medium", "weight": 5,
                       "plain": "They may keep your data for a long or unspecified time, even after you leave."},
    "legal_waiver": {"name": "Rights waiver", "risk": "medium", "weight": 5,
                     "plain": "You give up legal rights, for example through arbitration or broad content licences."},
    "policy_changes": {"name": "Silent changes", "risk": "low", "weight": 3,
                       "plain": "They can change the rules without asking you again."},
    "children": {"name": "Children's data", "risk": "info", "weight": 0,
                 "plain": "The policy says how children's data is handled."},
    "user_rights": {"name": "Your rights", "risk": "positive", "weight": -4,
                    "plain": "You can access, correct or delete your data."},
    "security": {"name": "Security", "risk": "positive", "weight": -3,
                 "plain": "They describe real security measures to protect your data."},
    "consent_control": {"name": "Consent & control", "risk": "positive", "weight": -4,
                        "plain": "You get choices: opt-outs, cookie controls or a no-sale promise."},
}

NEGATION = re.compile(
    r"\b(do not|does not|don't|doesn't|never|will not|won't|no longer|not)\b[^.]{0,40}\b(sell|rent|trade|share)\b",
    re.I,
)

RULES = [
    ("data_selling", re.compile(r"\b(sell|sold|selling|rent|trade)\b[^.]{0,60}\b(personal|data|information)\b", re.I)),
    ("sensitive_data", re.compile(r"\b(biometric|precise (geo)?location|geolocation|health (data|information)|fingerprint)\b", re.I)),
    ("legal_waiver", re.compile(r"\b(class action|binding arbitration|indemnify)\b", re.I)),
    ("long_retention", re.compile(r"\b(indefinitely|as long as (we )?(deem|need|necessary))\b", re.I)),
]

_model = None


def _build():
    X, y = [], []
    for label, sentences in TRAINING.items():
        for s in sentences:
            X.append(s)
            y.append(label)
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, lowercase=True, stop_words="english")),
        ("clf", LogisticRegression(C=8, max_iter=2000, class_weight="balanced")),
    ])
    pipe.fit(X, y)
    return pipe


def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            try:
                _model = joblib.load(MODEL_PATH)
            except Exception:
                _model = None
        if _model is None:
            _model = _build()
            try:
                joblib.dump(_model, MODEL_PATH)
            except Exception:
                pass
    return _model


def classify_sentences(sentences, threshold=0.34):
    """Return [{text,label,confidence}] for every sentence that is NOT neutral."""
    if not sentences:
        return []
    model = get_model()
    probs = model.predict_proba(sentences)
    classes = list(model.classes_)
    out = []
    for text, p in zip(sentences, probs):
        best = max(range(len(classes)), key=lambda i: p[i])
        label, conf = str(classes[best]), float(p[best])
        negated = bool(NEGATION.search(text))

        # rules can rescue / override the model
        for rule_label, rx in RULES:
            if rx.search(text):
                if negated and rule_label == "data_selling":
                    label, conf = "consent_control", max(conf, 0.7)
                elif label in ("neutral", rule_label) or conf < 0.5:
                    label, conf = rule_label, max(conf, 0.6)
                break
        else:
            if negated and label in ("data_selling", "third_party_sharing"):
                label, conf = "consent_control", max(conf, 0.6)

        if label == "neutral" or conf < threshold:
            continue
        out.append({"text": text, "label": label, "confidence": round(conf, 2)})
    return out
