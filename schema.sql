drop table if exists jokes;
create table jokes (
    id integer primary key autoincrement,
    joke string not null,
    track_id integer not null,
    rank integer not null
);

