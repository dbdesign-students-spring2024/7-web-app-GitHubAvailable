# Flask-MongoDB Web App

In this assignment you will create a web app that relies upon a MongoDB database.
<!--
Replace the contents of this file with a description of your own web app, as described in [the instructions](./instructions.md).
-->

## Words List Manager Lite

### Description
**Words List Manager Lite** is a web application based on MongoDB designed to allow users to create words list which one could learn using my incoming app **Words Helper**, an app that allows one to create words list and learn new words based on personal needs.

This app allows users to:
+ Create new words list;
+ Download existing words list;
+ Edit existing words list:
  * Renaming the words list
  * Changing the data stored inside the words list
+ Delete an existing words lists.

### Structure
Each words list is stored separately as a collection, and each word is stored as a single document in a specific words list. Each word has several fields:
+ `_id` - (*Not Visible to User*) the ObjectID of the word
+ `key` - the word (e.g., `Server`)
+ `notes` - a brief description of the meaning of the word (e.g., `Requests handler`)
+ `pronounciation` - the pronounciation of the word (e.g., `[ˈsər-vər]`)
+ `proficiency` - the user's familiarity with that word on a scale of 1 to 5, with `1` representing never seen before, and `5` representing clearly understand its meaning and usage
+ `description` - a detailed description of the word (e.g., `A MongoDB server is ...`)
+ `created` - (*Not Visible to User*) the time the word is added to the collection.

Note that as users can manage words lists and edit the data in each words lists, this application implemented **CRUD** in **2** levels:
+ Of documents (words);
+ Of collections (words lists).

### Versions Available
Web-Deployed: [(NYU i6 server)](https://i6.cims.nyu.edu/~hl4963/7-web-app-GitHubAvailable/flask.cgi).

### Contributor
This app is developed by entirely by me, Mark Liu: 
+ NetID: hl4963
+ GitHub: [GitHubAvailable](https://github.com/GitHubAvailable)