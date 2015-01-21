#!/usr/bin/env ambari-python-wrap
"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

class HDP22StackAdvisor(HDP21StackAdvisor):

  def getServiceConfigurationRecommenderDict(self):
    parentRecommendConfDict = super(HDP22StackAdvisor, self).getServiceConfigurationRecommenderDict()
    childRecommendConfDict = {
      "HDFS": self.recommendHDFSConfigurations,
      "HIVE": self.recommendHIVEConfigurations,
      "HBASE": self.recommendHBASEConfigurations,
      "MAPREDUCE2": self.recommendMapReduce2Configurations,
      "TEZ": self.recommendTezConfigurations,
      "AMS": self.recommendAmsConfigurations,
      "YARN": self.recommendYARNConfigurations
    }
    parentRecommendConfDict.update(childRecommendConfDict)
    return parentRecommendConfDict

  def recommendYARNConfigurations(self, configurations, clusterData, services, hosts):
    super(HDP22StackAdvisor, self).recommendYARNConfigurations(configurations, clusterData, services, hosts)
    putYarnProperty = self.putProperty(configurations, "yarn-site")
    putYarnProperty('yarn.nodemanager.resource.cpu-vcores', clusterData['cpu'])

  def recommendHDFSConfigurations(self, configurations, clusterData, services, hosts):
    putHdfsProperty = self.putProperty(configurations, "hdfs-site")
    putHdfsProperty("dfs.datanode.max.transfer.threads", 16384 if clusterData["hBaseInstalled"] else 4096)
    putHDFSProperty = self.putProperty(configurations, "hadoop-env")
    putHDFSProperty('namenode_heapsize', max(int(clusterData['totalAvailableRam'] / 2), 1024))
    putHDFSProperty = self.putProperty(configurations, "hadoop-env")
    putHDFSProperty('namenode_opt_newsize', max(int(clusterData['totalAvailableRam'] / 8), 128))
    putHDFSProperty = self.putProperty(configurations, "hadoop-env")
    putHDFSProperty('namenode_opt_maxnewsize', max(int(clusterData['totalAvailableRam'] / 8), 256))
    servicesList = [service["StackServices"]["service_name"] for service in services["services"]]
    if 'ranger-hdfs-plugin-properties' in services['configurations']:
      rangerPluginEnabled = services['configurations']['ranger-hdfs-plugin-properties']['properties']['ranger-hdfs-plugin-enabled']
      if ("RANGER" in servicesList) and (rangerPluginEnabled.lower() == 'Yes'.lower()):
        putHDFSProperty("dfs.permissions.enabled",'true')

  def recommendHIVEConfigurations(self, configurations, clusterData, services, hosts):
    servicesList = [service["StackServices"]["service_name"] for service in services["services"]]
    if 'ranger-hive-plugin-properties' in services['configurations']:
      rangerPluginEnabled = services['configurations']['ranger-hive-plugin-properties']['properties']['ranger-hive-plugin-enabled']
      if ("RANGER" in servicesList) :
        if (rangerPluginEnabled.lower() == "Yes".lower()):
          putHiveProperty = self.putProperty(configurations, "hiveserver2-site")
          putHiveProperty("hive.security.authorization.manager", 'com.xasecure.authorization.hive.authorizer.XaSecureHiveAuthorizerFactory')
          putHiveProperty("hive.security.authenticator.manager", 'org.apache.hadoop.hive.ql.security.SessionStateUserAuthenticator')
        elif (rangerPluginEnabled.lower() == "No".lower()):
          putHiveProperty = self.putProperty(configurations, "hiveserver2-site")
          putHiveProperty("hive.security.authorization.manager", 'org.apache.hadoop.hive.ql.security.authorization.DefaultHiveAuthorizationProvider')
          putHiveProperty("hive.security.authenticator.manager", 'org.apache.hadoop.hive.ql.security.HadoopDefaultAuthenticator')

  def recommendHBASEConfigurations(self, configurations, clusterData, services, hosts):
    putHbaseSiteProperty = self.putProperty(configurations, "hbase-site")
    putHbaseSiteProperty("hbase.regionserver.global.memstore.upperLimit", '0.4')

    servicesList = [service["StackServices"]["service_name"] for service in services["services"]]
    if 'ranger-hbase-plugin-properties' in services['configurations']:
      rangerPluginEnabled = services['configurations']['ranger-hbase-plugin-properties']['properties']['ranger-hbase-plugin-enabled']
      if ("RANGER" in servicesList) and (rangerPluginEnabled.lower() == "Yes".lower()):
          putHbaseSiteProperty("hbase.security.authorization", 'true')
          putHbaseSiteProperty("hbase.coprocessor.master.classes", 'com.xasecure.authorization.hbase.XaSecureAuthorizationCoprocessor')
          putHbaseSiteProperty("hbase.coprocessor.region.classes", 'com.xasecure.authorization.hbase.XaSecureAuthorizationCoprocessor')

  def recommendTezConfigurations(self, configurations, clusterData, services, hosts):
    putTezProperty = self.putProperty(configurations, "tez-site")
    putTezProperty("tez.am.resource.memory.mb", int(clusterData['amMemory']) * 2 if int(clusterData['amMemory']) < 3072 else int(clusterData['amMemory']))

    taskResourceMemory = clusterData['mapMemory'] if clusterData['mapMemory'] > 2048 else int(clusterData['reduceMemory'])
    taskResourceMemory = min(clusterData['containers'] * clusterData['ramPerContainer'], taskResourceMemory)
    putTezProperty("tez.task.resource.memory.mb", taskResourceMemory)
    putTezProperty("tez.runtime.io.sort.mb", min(int(taskResourceMemory * 0.4), 2047))
    putTezProperty("tez.runtime.unordered.output.buffer.size-mb", int(taskResourceMemory * 0.075))

  def recommendAmsConfigurations(self, configurations, clusterData, services, hosts):
    putAmsHbaseSiteProperty = self.putProperty(configurations, "ams-hbase-site")
    putTimelineServiceProperty = self.putProperty(configurations, "ams-site")
    putHbaseEnvProperty = self.putProperty(configurations, "ams-hbase-env")

    amsCollectorHosts = self.getComponentHostNames(services, "AMS", "METRIC_COLLECTOR")

    # TODO recommend configuration for multiple AMS collectors
    if len(amsCollectorHosts) > 1:
      pass
    else:
      totalHostsCount = len(hosts["items"])
      # TODO Tune values according to performance testing results
      if totalHostsCount > 400:
        putAmsHbaseSiteProperty("hfile.block.cache.size", 0.3)
        putAmsHbaseSiteProperty("hbase.regionserver.global.memstore.upperLimit", 0.5)
        putAmsHbaseSiteProperty("hbase.regionserver.global.memstore.lowerLimit", 0.4)
        putTimelineServiceProperty("timeline.metrics.host.aggregator.ttl", 86400)

        putHbaseEnvProperty("hbase_master_heapsize", "8096m")
        putHbaseEnvProperty("hbase_regionserver_heapsize", "8096m")
      elif totalHostsCount > 100:
        putAmsHbaseSiteProperty("hfile.block.cache.size", 0.3)
        putAmsHbaseSiteProperty("hbase.regionserver.global.memstore.upperLimit", 0.5)
        putAmsHbaseSiteProperty("hbase.regionserver.global.memstore.lowerLimit", 0.4)
        putTimelineServiceProperty("timeline.metrics.host.aggregator.ttl", 86400)

        putHbaseEnvProperty("hbase_master_heapsize", "2048m")
        putHbaseEnvProperty("hbase_regionserver_heapsize", "2048m")
      else:
        putAmsHbaseSiteProperty("hfile.block.cache.size", 0.3)
        putAmsHbaseSiteProperty("hbase.regionserver.global.memstore.upperLimit", 0.5)
        putAmsHbaseSiteProperty("hbase.regionserver.global.memstore.lowerLimit", 0.4)
        putTimelineServiceProperty("timeline.metrics.host.aggregator.ttl", 86400)

        putHbaseEnvProperty("hbase_master_heapsize", "1024m")
        putHbaseEnvProperty("hbase_regionserver_heapsize", "1024m")

  def getServiceConfigurationValidators(self):
    parentValidators = super(HDP22StackAdvisor, self).getServiceConfigurationValidators()
    childValidators = {
      "HDFS": {"hdfs-site": self.validateHDFSConfigurations,
               "hadoop-env": self.validateHDFSConfigurationsEnv},
      "HIVE": {"hiveserver2-site": self.validateHIVEConfigurations},
      "HBASE": {"hbase-site": self.validateHBASEConfigurations},
      "MAPREDUCE2": {"mapred-site": self.validateMapReduce2Configurations},
      "AMS": {"ams-hbase-site": self.validateAmsHbaseSiteConfigurations,
              "ams-hbase-env": self.validateAmsHbaseEnvConfigurations,
              "ams-site": self.validateAmsSiteConfigurations},
      "TEZ": {"tez-site": self.validateTezConfigurations}
    }
    parentValidators.update(childValidators)
    return parentValidators

  def validateTezConfigurations(self, properties, recommendedDefaults, configurations, services, hosts):
    validationItems = [ {"config-name": 'tez.am.resource.memory.mb', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'tez.am.resource.memory.mb')},
                        {"config-name": 'tez.task.resource.memory.mb', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'tez.task.resource.memory.mb')},
                        {"config-name": 'tez.runtime.io.sort.mb', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'tez.runtime.io.sort.mb')},
                        {"config-name": 'tez.runtime.unordered.output.buffer.size-mb', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'tez.runtime.unordered.output.buffer.size-mb')},]
    return self.toConfigurationValidationProblems(validationItems, "tez-site")

  def validateAmsSiteConfigurations(self, properties, recommendedDefaults, configurations, services, hosts):
    validationItems = []

    op_mode = properties.get("timeline.metrics.service.operation.mode")
    correct_op_mode_item = None
    if op_mode not in ("embedded", "distributed"):
      correct_op_mode_item = self.getErrorItem("Correct value should be set.")
      pass

    validationItems.extend([{"config-name":'timeline.metrics.service.operation.mode', "item": correct_op_mode_item }])
    return self.toConfigurationValidationProblems(validationItems, "ams-site")

  def validateAmsHbaseSiteConfigurations(self, properties, recommendedDefaults, configurations, services, hosts):

    amsCollectorHosts = self.getComponentHostNames(services, "AMS", "METRIC_COLLECTOR")
    ams_site = getSiteProperties(configurations, "ams-site")

    recommendedDiskSpace = 10485760
    # TODO validate configuration for multiple AMS collectors
    if len(amsCollectorHosts) > 1:
      pass
    else:
      totalHostsCount = len(hosts["items"])
      if totalHostsCount > 400:
        recommendedDiskSpace  = 104857600  # * 1k == 100 Gb
      elif totalHostsCount > 100:
        recommendedDiskSpace  = 52428800  # * 1k == 50 Gb
      elif totalHostsCount > 10:
        recommendedDiskSpace  = 20971520  # * 1k == 20 Gb


    validationItems = []
    for collectorHostName in amsCollectorHosts:
      for host in hosts["items"]:
        if host["Hosts"]["host_name"] == collectorHostName:
          validationItems.extend([ {"config-name": 'hbase.rootdir', "item": self.validatorEnoughDiskSpace(properties, 'hbase.rootdir', host["Hosts"], recommendedDiskSpace)}])
          break

    rootdir_item = None
    op_mode = ams_site.get("timeline.metrics.service.operation.mode")
    hbase_rootdir = properties.get("hbase.rootdir")
    if op_mode == "distributed" and not hbase_rootdir.startswith("hdfs://"):
      rootdir_item = self.getWarnItem("In distributed mode hbase.rootdir should point to HDFS. Collector will operate in embedded mode otherwise.")
      pass

    distributed_item = None
    distributed = properties.get("hbase.cluster.distributed")
    if hbase_rootdir.startswith("hdfs://") and not distributed.lower() == "true":
      distributed_item = self.getErrorItem("Distributed property should be set to true if hbase.rootdir points to HDFS.")

    validationItems.extend([{"config-name":'hbase.rootdir', "item": rootdir_item },
                            {"config-name":'hbase.cluster.distributed', "item": distributed_item }])

    return self.toConfigurationValidationProblems(validationItems, "ams-hbase-site")

  def validateAmsHbaseEnvConfigurations(self, properties, recommendedDefaults, configurations, services, hosts):
    regionServerItem = self.validatorLessThenDefaultValue(properties, recommendedDefaults, "hbase_regionserver_heapsize")
    masterItem = self.validatorLessThenDefaultValue(properties, recommendedDefaults, "hbase_master_heapsize")
    ams_env = getSiteProperties(configurations, "ams-env")
    logDirItem = self.validatorEqualsPropertyItem(properties, "hbase_log_dir",
                                                  ams_env, "ams_collector_log_dir")

    if masterItem is None:
      hbase_master_heapsize = formatXmxSizeToBytes(properties["hbase_master_heapsize"])

      # TODO Add AMS Collector Xmx property to ams-env
      # Collector 512m + HBASE Master heapsize
      # For standalone HBase, master's heap memory is used by regionserver as well
      requiredMemory = 536870912 + hbase_master_heapsize

      amsCollectorHosts = self.getComponentHostNames(services, "AMS", "METRIC_COLLECTOR")
      for collectorHostName in amsCollectorHosts:
        for host in hosts["items"]:
          if host["Hosts"]["host_name"] == collectorHostName:
            if host["Hosts"]["total_mem"] * 1024 < requiredMemory:  # in bytes
              message = "Not enough total RAM on the host {0}, " \
                        "at least {1} MB required" \
                        .format(collectorHostName, requiredMemory/1048576)  # MB
              regionServerItem = self.getWarnItem(message)
              masterItem = self.getWarnItem(message)
              break

    validationItems = [{"config-name": "hbase_regionserver_heapsize", "item": regionServerItem},
                       {"config-name": "hbase_master_heapsize", "item": masterItem},
                       {"config-name": "hbase_log_dir", "item": logDirItem}]
    return self.toConfigurationValidationProblems(validationItems, "ams-hbase-env")

  def recommendMapReduce2Configurations(self, configurations, clusterData, services, hosts):
    putMapredProperty = self.putProperty(configurations, "mapred-site")
    putMapredProperty('yarn.app.mapreduce.am.resource.mb', int(clusterData['amMemory']))
    putMapredProperty('yarn.app.mapreduce.am.command-opts', "-Xmx" + str(int(round(0.8 * clusterData['amMemory']))) + "m" + " -Dhdp.version=${hdp.version}")
    putMapredProperty('mapreduce.map.memory.mb', clusterData['mapMemory'])
    putMapredProperty('mapreduce.reduce.memory.mb', int(clusterData['reduceMemory']))
    putMapredProperty('mapreduce.map.java.opts', "-Xmx" + str(int(round(0.8 * clusterData['mapMemory']))) + "m")
    putMapredProperty('mapreduce.reduce.java.opts', "-Xmx" + str(int(round(0.8 * clusterData['reduceMemory']))) + "m")
    putMapredProperty('mapreduce.task.io.sort.mb', min(int(round(0.4 * clusterData['mapMemory'])), 1024))

  def validateMapReduce2Configurations(self, properties, recommendedDefaults, configurations, services, hosts):
    validationItems = [ {"config-name": 'mapreduce.map.java.opts', "item": self.validateXmxValue(properties, recommendedDefaults, 'mapreduce.map.java.opts')},
                        {"config-name": 'mapreduce.reduce.java.opts', "item": self.validateXmxValue(properties, recommendedDefaults, 'mapreduce.reduce.java.opts')},
                        {"config-name": 'mapreduce.task.io.sort.mb', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'mapreduce.task.io.sort.mb')},
                        {"config-name": 'mapreduce.map.memory.mb', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'mapreduce.map.memory.mb')},
                        {"config-name": 'mapreduce.reduce.memory.mb', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'mapreduce.reduce.memory.mb')},
                        {"config-name": 'yarn.app.mapreduce.am.resource.mb', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'yarn.app.mapreduce.am.resource.mb')}]
    return self.toConfigurationValidationProblems(validationItems, "mapred-site")

  def validateHDFSConfigurationsEnv(self, properties, recommendedDefaults, configurations, services, hosts):
    validationItems = [ {"config-name": 'namenode_heapsize', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'namenode_heapsize')},
                        {"config-name": 'namenode_opt_newsize', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'namenode_opt_newsize')},
                        {"config-name": 'namenode_opt_maxnewsize', "item": self.validatorLessThenDefaultValue(properties, recommendedDefaults, 'namenode_opt_maxnewsize')}]
    return self.toConfigurationValidationProblems(validationItems, "hadoop-env")
  
  def validateHDFSConfigurations(self, properties, recommendedDefaults, configurations, services, hosts):
    # We can not access property hadoop.security.authentication from the
    # other config (core-site). That's why we are using another heuristics here
    hdfs_site = properties
    core_site = getSiteProperties(configurations, "core-site")

    dfs_encrypt_data_transfer = 'dfs.encrypt.data.transfer'  # Hadoop Wire encryption
    try:
      wire_encryption_enabled = hdfs_site[dfs_encrypt_data_transfer] == "true"
    except KeyError:
      wire_encryption_enabled = False

    HTTP_ONLY = 'HTTP_ONLY'
    HTTPS_ONLY = 'HTTPS_ONLY'
    HTTP_AND_HTTPS = 'HTTP_AND_HTTPS'

    VALID_HTTP_POLICY_VALUES = [HTTP_ONLY, HTTPS_ONLY, HTTP_AND_HTTPS]
    VALID_TRANSFER_PROTECTION_VALUES = ['authentication', 'integrity', 'privacy']

    validationItems = []
    #Adding Ranger Plugin logic here 
    ranger_plugin_properties = getSiteProperties(configurations, "ranger-hdfs-plugin-properties")
    ranger_plugin_enabled = ranger_plugin_properties['ranger-hdfs-plugin-enabled']
    servicesList = [service["StackServices"]["service_name"] for service in services["services"]]
    if ("RANGER" in servicesList) and (ranger_plugin_enabled.lower() == 'Yes'.lower()):
      if hdfs_site['dfs.permissions.enabled'] != 'true':
        validationItems.append({"config-name": 'dfs.permissions.enabled',
                                    "item": self.getWarnItem(
                                      "dfs.permissions.enabled needs to be set to true if Ranger HDFS Plugin is enabled.")})

    if (not wire_encryption_enabled and   # If wire encryption is enabled at Hadoop, it disables all our checks
          core_site['hadoop.security.authentication'] == 'kerberos' and
          core_site['hadoop.security.authorization'] == 'true'):
      # security is enabled

      dfs_http_policy = 'dfs.http.policy'
      dfs_datanode_address = 'dfs.datanode.address'
      datanode_http_address = 'dfs.datanode.http.address'
      datanode_https_address = 'dfs.datanode.https.address'
      data_transfer_protection = 'dfs.data.transfer.protection'

      try: # Params may be absent
        privileged_dfs_dn_port = isSecurePort(getPort(hdfs_site[dfs_datanode_address]))
      except KeyError:
        privileged_dfs_dn_port = False
      try:
        privileged_dfs_http_port = isSecurePort(getPort(hdfs_site[datanode_http_address]))
      except KeyError:
        privileged_dfs_http_port = False
      try:
        privileged_dfs_https_port = isSecurePort(getPort(hdfs_site[datanode_https_address]))
      except KeyError:
        privileged_dfs_https_port = False
      try:
        dfs_http_policy_value = hdfs_site[dfs_http_policy]
      except KeyError:
        dfs_http_policy_value = HTTP_ONLY  # Default
      try:
        data_transfer_protection_value = hdfs_site[data_transfer_protection]
      except KeyError:
        data_transfer_protection_value = None

      if dfs_http_policy_value not in VALID_HTTP_POLICY_VALUES:
        validationItems.append({"config-name": dfs_http_policy,
                                "item": self.getWarnItem(
                                  "Invalid property value: {0}. Valid values are {1}".format(
                                    dfs_http_policy_value, VALID_HTTP_POLICY_VALUES))})

      # determine whether we use secure ports
      address_properties_with_warnings = []
      if dfs_http_policy_value == HTTPS_ONLY:
        if not privileged_dfs_dn_port and (privileged_dfs_https_port or datanode_https_address not in hdfs_site):
          important_properties = [dfs_datanode_address, datanode_https_address]
          message = "You set up datanode to use some non-secure ports. " \
                    "If you want to run Datanode under non-root user in a secure cluster, " \
                    "you should set all these properties {2} " \
                    "to use non-secure ports (if property {3} does not exist, " \
                    "just add it). You may also set up property {4} ('{5}' is a good default value). " \
                    "Also, set up WebHDFS with SSL as " \
                    "described in manual in order to be able to " \
                    "use HTTPS.".format(dfs_http_policy, dfs_http_policy_value, important_properties,
                                        datanode_https_address, data_transfer_protection,
                                        VALID_TRANSFER_PROTECTION_VALUES[0])
          address_properties_with_warnings.extend(important_properties)
      else:  # dfs_http_policy_value == HTTP_AND_HTTPS or HTTP_ONLY
        # We don't enforce datanode_https_address to use privileged ports here
        any_nonprivileged_ports_are_in_use = not privileged_dfs_dn_port or not privileged_dfs_http_port
        if any_nonprivileged_ports_are_in_use:
          important_properties = [dfs_datanode_address, datanode_http_address]
          message = "You have set up datanode to use some non-secure ports, but {0} is set to {1}. " \
                    "In a secure cluster, Datanode forbids using non-secure ports " \
                    "if {0} is not set to {3}. " \
                    "Please make sure that properties {2} use secure ports.".format(
                      dfs_http_policy, dfs_http_policy_value, important_properties, HTTPS_ONLY)
          address_properties_with_warnings.extend(important_properties)

      # Generate port-related warnings if any
      for prop in address_properties_with_warnings:
        validationItems.append({"config-name": prop,
                                "item": self.getWarnItem(message)})

      # Check if it is appropriate to use dfs.data.transfer.protection
      if data_transfer_protection_value is not None:
        if dfs_http_policy_value in [HTTP_ONLY, HTTP_AND_HTTPS]:
          validationItems.append({"config-name": data_transfer_protection,
                                  "item": self.getWarnItem(
                                    "{0} property can not be used when {1} is set to any "
                                    "value other then {2}. Tip: When {1} property is not defined, it defaults to {3}".format(
                                    data_transfer_protection, dfs_http_policy, HTTPS_ONLY, HTTP_ONLY))})
        elif not data_transfer_protection_value in VALID_TRANSFER_PROTECTION_VALUES:
          validationItems.append({"config-name": data_transfer_protection,
                                  "item": self.getWarnItem(
                                    "Invalid property value: {0}. Valid values are {1}.".format(
                                      data_transfer_protection_value, VALID_TRANSFER_PROTECTION_VALUES))})
    return self.toConfigurationValidationProblems(validationItems, "hdfs-site")

  def validateHIVEConfigurations(self, properties, recommendedDefaults, configurations, services, hosts):
    hive_server2 = properties
    validationItems = [] 
    #Adding Ranger Plugin logic here 
    ranger_plugin_properties = getSiteProperties(configurations, "ranger-hive-plugin-properties")
    ranger_plugin_enabled = ranger_plugin_properties['ranger-hive-plugin-enabled']
    servicesList = [service["StackServices"]["service_name"] for service in services["services"]]
    ##Add stack validations only if Ranger is enabled.
    if ("RANGER" in servicesList):
      ##Add stack validations for  Ranger plugin enabled.
      if (ranger_plugin_enabled.lower() == 'Yes'.lower()):
        prop_name = 'hive.security.authorization.manager'
        prop_val = "com.xasecure.authorization.hive.authorizer.XaSecureHiveAuthorizerFactory"
        if hive_server2[prop_name] != prop_val:
          validationItems.append({"config-name": prop_name,
                                  "item": self.getWarnItem(
                                  "If Ranger HIVE Plugin is enabled."\
                                  " {0} needs to be set to {1}".format(prop_name,prop_val))})
        prop_name = 'hive.security.authenticator.manager'
        prop_val = "org.apache.hadoop.hive.ql.security.SessionStateUserAuthenticator"
        if hive_server2[prop_name] != prop_val:
          validationItems.append({"config-name": prop_name,
                                  "item": self.getWarnItem(
                                  "If Ranger HIVE Plugin is enabled."\
                                  " {0} needs to be set to {1}".format(prop_name,prop_val))})
      ##Add stack validations for  Ranger plugin disabled.
      elif (ranger_plugin_enabled.lower() == 'No'.lower()):
        prop_name = 'hive.security.authorization.manager'
        prop_val = "org.apache.hadoop.hive.ql.security.authorization.DefaultHiveAuthorizationProvider"
        if hive_server2[prop_name] != prop_val:
          validationItems.append({"config-name": prop_name,
                                  "item": self.getWarnItem(
                                  "If Ranger HIVE Plugin is disabled."\
                                  " {0} needs to be set to {1}".format(prop_name,prop_val))})
        prop_name = 'hive.security.authenticator.manager'
        prop_val = "org.apache.hadoop.hive.ql.security.HadoopDefaultAuthenticator"
        if hive_server2[prop_name] != prop_val:
          validationItems.append({"config-name": prop_name,
                                  "item": self.getWarnItem(
                                  "If Ranger HIVE Plugin is disabled."\
                                  " {0} needs to be set to {1}".format(prop_name,prop_val))})
    return self.toConfigurationValidationProblems(validationItems, "hiveserver2-site")

  def validateHBASEConfigurations(self, properties, recommendedDefaults, configurations, services, hosts):
    hbase_site = properties
    validationItems = []

    prop_name1 = 'hbase.regionserver.global.memstore.upperLimit'
    prop_name2 = 'hfile.block.cache.size'
    props_max_sum = 0.8

    if not is_number(hbase_site[prop_name1]):
      validationItems.append({"config-name": prop_name1,
                              "item": self.getWarnItem(
                              "{0} should be float value".format(prop_name1))})
    elif not is_number(hbase_site[prop_name2]):
      validationItems.append({"config-name": prop_name2,
                              "item": self.getWarnItem(
                              "{0} should be float value".format(prop_name2))})
    elif float(hbase_site[prop_name1]) + float(hbase_site[prop_name2]) > props_max_sum:
      validationItems.append({"config-name": prop_name1,
                              "item": self.getWarnItem(
                              "{0} and {1} sum should not exceed {2}".format(prop_name1, prop_name2, props_max_sum))})

    #Adding Ranger Plugin logic here 
    ranger_plugin_properties = getSiteProperties(configurations, "ranger-hbase-plugin-properties")
    ranger_plugin_enabled = ranger_plugin_properties['ranger-hbase-plugin-enabled']
    prop_name = 'hbase.security.authorization'
    prop_val = "true"
    servicesList = [service["StackServices"]["service_name"] for service in services["services"]]
    if ("RANGER" in servicesList) and (ranger_plugin_enabled.lower() == 'Yes'.lower()):
      if hbase_site[prop_name] != prop_val:
        validationItems.append({"config-name": prop_name,
                                "item": self.getWarnItem(
                                "If Ranger HBASE Plugin is enabled."\
                                "{0} needs to be set to {1}".format(prop_name,prop_val))})
      prop_name = "hbase.coprocessor.master.classes"
      prop_val = "com.xasecure.authorization.hbase.XaSecureAuthorizationCoprocessor"
      if hbase_site[prop_name] != prop_val:
        validationItems.append({"config-name": prop_name,
                                "item": self.getWarnItem(
                                "If Ranger HBASE Plugin is enabled."\
                                " {0} needs to be set to {1}".format(prop_name,prop_val))})
      prop_name = "hbase.coprocessor.region.classes"
      prop_val = "com.xasecure.authorization.hbase.XaSecureAuthorizationCoprocessor"
      if hbase_site[prop_name] != prop_val:
        validationItems.append({"config-name": prop_name,
                                "item": self.getWarnItem(
                                "If Ranger HBASE Plugin is enabled."\
                                " {0} needs to be set to {1}".format(prop_name,prop_val))})
    return self.toConfigurationValidationProblems(validationItems, "hbase-site")

  def getMastersWithMultipleInstances(self):
    result = super(HDP22StackAdvisor, self).getMastersWithMultipleInstances()
    result.extend(['METRIC_COLLECTOR'])
    return result

  def getNotValuableComponents(self):
    result = super(HDP22StackAdvisor, self).getNotValuableComponents()
    result.extend(['METRIC_MONITOR'])
    return result

  def getNotPreferableOnServerComponents(self):
    result = super(HDP22StackAdvisor, self).getNotPreferableOnServerComponents()
    result.extend(['METRIC_COLLECTOR'])
    return result

  def getCardinalitiesDict(self):
    result = super(HDP22StackAdvisor, self).getCardinalitiesDict()
    result['METRIC_COLLECTOR'] = {"min": 1}
    return result

  def getComponentLayoutSchemes(self):
    result = super(HDP22StackAdvisor, self).getComponentLayoutSchemes()
    result['METRIC_COLLECTOR'] = {"else": 2}
    return result

def is_number(s):
  try:
    float(s)
    return True
  except ValueError:
    pass

  return False
