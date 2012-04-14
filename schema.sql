drop table if exists jokes;
create table jokes (
    id integer primary key autoincrement,
    joke string not null,
    rank integer not null
);

