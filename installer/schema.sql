-- Non-destructive first-run schema for the WMS installer.
-- Unlike Baza_SQL.sql, this file never drops or resets tables.

CREATE DATABASE IF NOT EXISTS `mydb` CHARACTER SET utf8mb4;
USE `mydb`;

CREATE TABLE IF NOT EXISTS `tow` (
  `tow_kod` VARCHAR(45) NOT NULL,
  `tow_name` VARCHAR(45) NULL,
  `ilo_is` DOUBLE NULL,
  `ce` DOUBLE NULL,
  `vat_rate` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `added_at` DATETIME NULL,
  `modified_at` DATETIME NULL,
  PRIMARY KEY (`tow_kod`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `odb` (
  `kod_odb` INT NOT NULL,
  `name_odb` VARCHAR(45) NULL,
  `nip` BIGINT(15) NULL,
  PRIMARY KEY (`kod_odb`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `dst` (
  `kod_dst` INT NOT NULL,
  `name_dst` VARCHAR(45) NULL,
  `nip` BIGINT(15) NULL,
  PRIMARY KEY (`kod_dst`)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `wz` (
  `idwz` INT NOT NULL AUTO_INCREMENT,
  `val` DOUBLE NULL,
  `odb_kod_odb` INT NOT NULL,
  `dok_id` VARCHAR(45) NULL,
  `issue_date` DATE NULL,
  PRIMARY KEY (`idwz`),
  KEY `fk_wz_odb1_idx` (`odb_kod_odb`),
  CONSTRAINT `fk_wz_odb1` FOREIGN KEY (`odb_kod_odb`)
    REFERENCES `odb` (`kod_odb`)
    ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `wz_p` (
  `idwz_p` INT NOT NULL AUTO_INCREMENT,
  `ilo` INT NULL,
  `val` DOUBLE NULL,
  `vat_rate` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `tow_tow_kod` VARCHAR(45) NOT NULL,
  `wz_idwz` INT NOT NULL,
  PRIMARY KEY (`idwz_p`),
  KEY `fk_wz_p_tow1_idx` (`tow_tow_kod`),
  KEY `fk_wz_p_wz1_idx` (`wz_idwz`),
  CONSTRAINT `fk_wz_p_tow1` FOREIGN KEY (`tow_tow_kod`)
    REFERENCES `tow` (`tow_kod`)
    ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_wz_p_wz1` FOREIGN KEY (`wz_idwz`)
    REFERENCES `wz` (`idwz`)
    ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `pz` (
  `idpz` INT NOT NULL AUTO_INCREMENT,
  `val` DOUBLE NULL,
  `dst_kod_dst` INT NOT NULL,
  `dok_id` VARCHAR(45) NULL,
  `issue_date` DATE NULL,
  PRIMARY KEY (`idpz`),
  KEY `fk_pz_dst1_idx` (`dst_kod_dst`),
  CONSTRAINT `fk_pz_dst1` FOREIGN KEY (`dst_kod_dst`)
    REFERENCES `dst` (`kod_dst`)
    ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS `pz_p` (
  `idpz_p` INT NOT NULL AUTO_INCREMENT,
  `ilo` INT NULL,
  `val` DOUBLE NULL,
  `vat_rate` DECIMAL(5,2) NOT NULL DEFAULT 0,
  `pz_idpz` INT NOT NULL,
  `tow_tow_kod` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`idpz_p`),
  KEY `fk_pz_p_pz1_idx` (`pz_idpz`),
  KEY `fk_pz_p_tow1_idx` (`tow_tow_kod`),
  CONSTRAINT `fk_pz_p_pz1` FOREIGN KEY (`pz_idpz`)
    REFERENCES `pz` (`idpz`)
    ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `fk_pz_p_tow1` FOREIGN KEY (`tow_tow_kod`)
    REFERENCES `tow` (`tow_kod`)
    ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB;
