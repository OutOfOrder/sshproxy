-- make backup before running this script
-- DO NOT RUN IT TWICE !!!

update login set `password` = sha1(`password`);
