# quick_13f

To create the database, please go to: https://www.sec.gov/dera/data/form-13f and download the forms. Unzip each one and place it in a folder under the project directory with the name format "2018q4_form13f".

You will need to run russell_downloader.py to get the stats for the securities (our investment universe). Next, run fill_database.py (ensuring all the form 13F folders are in the same directory).

Remember to migrate the database with **python manage.py makemigrations**.

Finally, run the project with **python manage.py runserver**.
