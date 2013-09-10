CREATE TABLE `skyline_hosts` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `value` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8;

CREATE TABLE `skyline_metrics` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `vaue` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8;

CREATE TABLE `skyline_anomalies` (
  `hostid` bigint(20) unsigned NOT NULL,
  `metricid` bigint(20) unsigned NOT NULL,
  `value` double(20,4) NOT NULL,
  `ts` int(11) NOT NULL,
  KEY `index_1` (`hostid`,`metricid`)
) ENGINE=TokuDB DEFAULT CHARSET=utf8;
