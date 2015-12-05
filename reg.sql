!drop table if exists events;
!create table events (
  id int not null auto_increment,
  name varchar (255) not null,
  state int not null,
  flags int not null,
  users int not null,
  fields int not null,
  user_fields int not null,
  primary key (id)
);
!drop table if exists teams;
!create table teams (
  id int not null auto_increment,
  name varchar (255) not null,
  email varchar (255) not null,
  state int not null,
  event_id int not null,
  primary key (id)
);
!drop table if exists users;
!create table users (
  id int not null auto_increment,
  team_id int not null,
  first_name varchar (255) not null,
  last_name varchar (255) not null,
  patronymic varchar (255) not null,
  school_name varchar (255) not null,
  grade int not null,
  group_name int not null,
  email varchar (255) not null,
  phone varchar (255) not null,
  vkid varchar (255) not null,
  state int not null,
  hashcode varchar (255) not null,
  primary key (id)
);

!insert into events
  (name, state, flags, users, fields, user_fields) values
  ("XXXVII Чемпионат СПбГУ", 0, 0, 3, 31, 31);
