// Front du quiz : HTML/CSS/JS statiques, sans framework ni étape de build.
// Toutes les requêtes partent vers /api/... : c'est nginx qui les relaie à l'API.

const etat = { pseudo: "", questions: [], indice: 0, reponses: {} };
const $ = (id) => document.getElementById(id);

function afficher(ecran) {
  for (const id of ["ecran-accueil", "ecran-question", "ecran-resultat"]) {
    $(id).hidden = id !== ecran;
  }
}

// Petit utilitaire : crée un élément avec du texte (textContent, jamais innerHTML,
// pour qu'un pseudo malicieux ne puisse pas injecter de HTML).
function el(balise, texte, classe) {
  const e = document.createElement(balise);
  if (texte !== undefined) e.textContent = texte;
  if (classe) e.className = classe;
  return e;
}

async function api(chemin, options) {
  const reponse = await fetch(chemin, options);
  if (!reponse.ok) throw new Error(`${chemin} a répondu ${reponse.status}`);
  return reponse.json();
}

async function chargerClassement() {
  const liste = $("classement");
  try {
    const donnees = await api("/api/leaderboard");
    liste.replaceChildren();
    if (donnees.classement.length === 0) liste.append(el("li", "Personne n'a encore joué."));
    for (const joueur of donnees.classement) {
      const li = el("li", joueur.pseudo);
      li.append(el("b", String(joueur.score)));
      liste.append(li);
    }
    $("source-classement").textContent = `Source : ${donnees.source}`;
  } catch (erreur) {
    liste.replaceChildren(el("li", "Classement indisponible.", "erreur"));
    $("source-classement").textContent = erreur.message;
  }
}

function afficherQuestion() {
  const q = etat.questions[etat.indice];
  $("progression").textContent = `Question ${etat.indice + 1} / ${etat.questions.length}`;
  $("texte-question").textContent = q.texte;
  const zone = $("choix");
  zone.replaceChildren();
  q.choix.forEach((texte, i) => {
    const bouton = el("button", texte);
    bouton.type = "button";
    bouton.addEventListener("click", () => repondre(q.id, i));
    zone.append(bouton);
  });
}

async function repondre(idQuestion, indiceChoix) {
  etat.reponses[idQuestion] = indiceChoix;
  etat.indice += 1;
  if (etat.indice < etat.questions.length) return afficherQuestion();

  const resultat = await api("/api/scores", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pseudo: etat.pseudo, reponses: etat.reponses }),
  });
  $("score").textContent = `${resultat.pseudo}, votre score : ${resultat.score} / ${resultat.total}`;
  const liste = $("correction");
  liste.replaceChildren();
  resultat.correction.forEach((c, i) => {
    const q = etat.questions[i];
    const li = el("li");
    li.append(el("span", c.correct ? "Juste. " : "Faux. ", c.correct ? "ok" : "ko"));
    li.append(document.createTextNode(q.texte));
    li.append(el("small", `Réponse : ${q.choix[c.bonne_reponse]}. ${c.explication}`));
    liste.append(li);
  });
  afficher("ecran-resultat");
  chargerClassement();
}

$("form-pseudo").addEventListener("submit", async (evenement) => {
  evenement.preventDefault();
  etat.pseudo = $("pseudo").value.trim();
  if (!etat.pseudo) return;
  try {
    etat.questions = await api("/api/questions");
    etat.indice = 0;
    etat.reponses = {};
    $("erreur-accueil").hidden = true;
    afficher("ecran-question");
    afficherQuestion();
  } catch (erreur) {
    $("erreur-accueil").textContent = `Impossible de charger les questions (${erreur.message}). L'API est-elle joignable ?`;
    $("erreur-accueil").hidden = false;
  }
});

$("rejouer").addEventListener("click", () => afficher("ecran-accueil"));

chargerClassement();
