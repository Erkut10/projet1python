import pandas as pd 
import requests
from scrapy import Selector
from urllib.parse import urljoin
import os
import argparse

#notre argument pour choisir la catégorie à scrap
parser = argparse.ArgumentParser(description="Scraper BooksToScrape par catégorie ou toutes")
parser.add_argument("--categorie", type=str, default="all", help="Nom exact de la catégorie à scraper (ou 'all' pour tout scraper)")
args = parser.parse_args()

#ici on récupère les catégories sur le site
url = "https://books.toscrape.com/"
rep = requests.get(url)
selector = Selector(text=rep.text)

categorie = selector.css("ul.nav-list ul li a::attr(href)").getall()[1:]
categorie_1 = selector.css("ul.nav-list ul li a::text").getall()[1:]
categorie_nom = [name.strip() for name in categorie_1]


#ici on crée les dossiers pour nos scraps
os.makedirs("outputs/csv", exist_ok=True)
os.makedirs("outputs/images", exist_ok=True)

#ici on choisit ce qu'on veut scrape
if args.categorie.lower() != "all":
    choix = args.categorie.strip().lower().replace("_", " ")
    categorie_nom_clean = [c.strip().lower() for c in categorie_nom]

    #on regarde si notre catégorie existe
    if choix not in categorie_nom_clean:
        print("Catégorie introuvable. Catégories disponibles :")
        print(categorie_nom)
        exit()

    #on isole notre choix    
    index = categorie_nom_clean.index(choix)
    categorie = [categorie[index]]
    categorie_nom = [categorie_nom[index]]
    print("Scraping de la catégorie :", categorie_nom[0])
    #sinon on scrape tout
else:
    print("Scraping de toutes les catégories.")

#notre boucle pour tout scrapper
for a, nom_cat in zip(categorie, categorie_nom):
    categorie_url = urljoin(url, a)
    livres_data = []

    page_url = categorie_url
    while True:
        rep_categorie = requests.get(page_url)
        selector_page = Selector(text=rep_categorie.text)

        livres = selector_page.css("h3 a::attr(href)").getall()

        #notre boucle pour chaque livre
        for i in livres:
            url_livres = urljoin(page_url, i)
            rep_livres = requests.get(url_livres)
            selector_prod = Selector(text=rep_livres.text)

            #notre prix du livre on le récupère
            prix = selector_prod.css("p.price_color::text").get()
            if prix:
                prix = prix.replace("Â", "") #ici on corrige bien le symbole du prix

            #notre titre du livre on le récupère
            titres_livre = selector_prod.css("h1::text").get()

            #pareil pour le stock
            stock_list = selector_prod.css("p.instock.availability::text").getall()
            stock = " ".join(s.strip() for s in stock_list if s.strip())

            #pareil on prend les notes
            note = (selector_prod.css("p.star-rating::attr(class)").get() or "star-rating None").split()[-1]
            
            #pareil pour l'upc
            upc = selector_prod.css("table td::text").get()
            #on prend l'image du produit
            img_path = selector_prod.css("img::attr(src)").get()
            img_path = img_path.replace("../../", "") if img_path else ""
            image = url + img_path

            nom_fichier = (upc + "_" + titres_livre).replace(" ", "_").replace("’", "_").replace("'", "_").replace("/", "_").replace("\\", "_")

            #onn fait notre dossier de la catégorie pour mettre les images dedans
            dossier_image = os.path.join("outputs/images", nom_cat.replace(" ", "_"))
            os.makedirs(dossier_image, exist_ok=True)
            chemin_image = os.path.join(dossier_image, nom_fichier + ".jpg")

            #on dl
            try:
                if image:
                    rep_img = requests.get(image)
                    with open(chemin_image, "wb") as f:
                        f.write(rep_img.content)
                else:
                    chemin_image = None
            except:
                chemin_image = None

            #toutes nos informations du livres
            livres_data.append({
                "categorie": nom_cat,
                "titre": titres_livre,
                "prix": prix,
                "stock": stock,
                "note": note,
                "upc": upc,
                "url_produit": url_livres,
                "url_image": image,
                "image_locale": chemin_image
            })

        #on vérifie bien si il y a une uatre page à chaque fois
        next_page = selector_page.css("li.next a::attr(href)").get()
        if next_page:
            page_url = urljoin(page_url, next_page)
        else:
            break

            #et voilà on génère notre csv pour notre catégorie
    csv_nom = "category_" + nom_cat.replace(" ", "_") + ".csv"
    csv_path = os.path.join("outputs/csv", csv_nom)
    pd.DataFrame(livres_data).to_csv(csv_path, index=False, encoding="utf-8-sig")
    print("CSV créé :", csv_path, "(", len(livres_data), "livres )")