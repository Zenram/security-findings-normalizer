AICPA SOC 2 Compliance Guide on AWS 

July 2025 



<!-- Start of picture text -->
aWws<br>I<br><!-- End of picture text -->

# No#ces 

Customers are responsible for making their own independent assessment of the informa6on in this document. This document: (a) is for informa6onal purposes only, (b) represents AWS’s current product offerings and prac6ces, which are subject to change without no6ce, and (c) does not create any commitments or assurances from AWS and its affiliates, suppliers or licensors. AWS products or services are provided “as is” without warran6es, representa6ons, or condi6ons of any kind, whether express or implied. The responsibili6es and liabili6es of AWS to its customers are controlled by AWS agreements, and this document is not part of, nor does it modify, any agreement between AWS and its customers. 

© 2025 Amazon Web Services, Inc. or its affiliates. All rights reserved. 

# Contents 

|Introduction ...................................................................................................................... 1|
|---|
|SOC 2 .............................................................................................................................. 2|
|Understanding the SOC 2 framework .............................................................................. 2|
|SOC 2 in AWS context .................................................................................................... 4|
|AWS Shared Responsibility model and its role in SOC 2 ................................................ 6|
|Complementary User En6ty Controls: Customer responsibili6es in the cloud ........................... 7|
|CUECs and the Shared Responsibility Model .............................................................................. 7|
|Applying SOC 2 TSC in AWS environments ................................................................... 9|
|CC1 series: Control Environment .............................................................................................. 10|
|CC2 series: Communica6on and Informa6on ........................................................................... 12|
|CC3 series: Risk Assessment ..................................................................................................... 14|
|CC4 series: Monitoring Ac6vi6es .............................................................................................. 16|
|CC5 series: Control Ac6vi6es .................................................................................................... 17|
|CC6 series: Logical and Physical Access Controls ...................................................................... 19|
|CC7 series: System Opera6ons .................................................................................................. 24|
|CC8 series: Change Management ............................................................................................. 27|
|CC9 series: Risk Mi6ga6on ........................................................................................................ 28|
|Category specific criteria and AWS guidance ................................................................ 30|
|PI series: Processing Integrity ................................................................................................... 30|
|A series: Availability .................................................................................................................. 33|
|C series: Confiden6ality ............................................................................................................ 35|
|P series: Privacy ......................................................................................................................... 36|
|Control design and documentation best practices ......................................................... 63|
|Efficient SOC 2 control ............................................................................................................... 63|
|Documen6ng controls in AWS environments ........................................................................... 63|
|Evidence collection and audit readiness ........................................................................ 64|



|AWS sources of evidence .......................................................................................................... 64|
|---|
|Evidence collec6on strategies ................................................................................................... 65|
|Risk and governance: SOC 2 for the executive team .................................................... 65|
|Conclusion and recommendations ................................................................................ 67|
|Key takeaways ........................................................................................................................... 67|
|Contributors ................................................................................................................... 67|
|Further reading .............................................................................................................. 68|
|Document revisions ....................................................................................................... 68|



# Abstract 

Effec6vely achieving Systems and Organiza6on Controls (SOC 2) compliance in AWS environments requires a principled yet prac6cal approach to implemen6ng controls that align with the AICPA’s Trust Services Criteria (TSC). Unlike checkbox-driven audits, SOC 2 emphasizes risk-based, con6nuous assurance of an organiza6on’s ability to protect systems and data across security, availability, processing integrity, confiden6ality, and privacy dimensions. 

This whitepaper provides guidance for organiza6ons designing and opera6ng workloads in Amazon Web Services (AWS) to meet SOC 2 expecta6ons. It focuses on transla6ng abstract control criteria into ac6onable technical and procedural controls—using AWS-na6ve services for automa6on, visibility, and enforcement. From iden6ty and access governance to incident response readiness, each control area is addressed with real-world AWS service mappings and implementa6on guidance. 

While AWS SOC reports cover the security of the cloud, this whitepaper emphasizes SOC 2 compliance in the cloud—focusing on the customer’s responsibili6es within their own AWS environment. 

Intended for cloud security architects, DevOps engineers, compliance leads, and third-party auditors, this paper demys6fies SOC 2’s flexible framework and demonstrates how AWS customers can confidently manage their control environment, prepare audit-ready evidence, and sustain ongoing compliance at scale. 

The content is for illustra6ve and educa6onal purposes only and does not cons6tute compliance or audit advice. Customers are responsible for interpre6ng and applying SOC2 requirements based on their specific environment. 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

# Introduc#on 

As service organiza6ons increasingly migrate their systems, workloads, and data to <u>Amazon Web Services (AWS), the need to demonstrate trust, accountability, and control effec6veness</u> becomes more cri6cal. Customers and business partners demand assurance that cloud-hosted systems are secure, available, confiden6al, and privacy-conscious. 

In this context, providing formal assurance through industry-standard frameworks is a strategic and opera6onal impera6ve. One of the most recognized and widely adopted assurance frameworks in the United States is <u>SOC 2 (System and Organiza6on Controls 2), developed by</u> the American Ins6tute of Cer6fied Public Accountants (AICPA). 

SOC 2 compliance and the examina6on associated with achieving a favorable SOC 2 report helps organiza6ons demonstrate that they have implemented effec6ve controls aligned to Trust Services Criteria (TSC) referenced in AICPA guides and that those controls operate consistently in AWS environments. 

The SOC 2 framework evaluates whether a service organiza6on’s systems are designed and opera6ng effec6vely to meet criteria in one or more of five categories: Security, Availability, Processing Integrity, Confiden6ality, and Privacy. These TSC, most recently updated in 2017, are principle-based and map to <u>COSO’s internal control framework.</u> 

**Note** : AWS SOC reports—represen6ng _of the cloud_ compliance—do not include the Processing Integrity category in their scope. Customers pursuing SOC 2 for their workloads in the cloud should independently assess and implement controls aligned to Processing Integrity, where applicable, based on their own service delivery commitment 

This whitepaper provides a structured, prac6cal guide for aligning AWS-based workloads and infrastructure with SOC 2 TSC. It is designed to help organiza6ons understand, implement, and maintain effec6ve controls that meet SOC 2 expecta6ons in the cloud. 

Readers will gain clarity on: 

- How SOC 2 criteria work 

- What controls are expected 

- How to implement and validate those controls in AWS 

- How to prepare evidence for Type 1 or Type 2 audits 



Page 1 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

This paper is designed for security architects, compliance professionals, DevOps engineers, auditors, and any stakeholder seeking audit readiness and opera6onal assurance in AWS. 

# SOC 2 

System and Organiza6on Controls 2 (SOC 2) is a compliance framework developed by the American Ins6tute of Cer6fied Public Accountants (AICPA) to help service organiza6ons demonstrate that their systems are designed and opera6ng effec6vely to meet categories related to: 

- Security 

- Processing Integrity 

- Availability 

- Confiden6ality 

- Privacy 

These are collec6vely known as the _Trust Services Criteria (TSC 2017)_ . Each organiza6on undergoing a SOC 2 audit must select which categories are applicable based on the nature of its services and customer commitments. SOC 2 examina6on comes in two types: 

- **Type 1:** Examines the design of controls at a point in 6me 

- **Type 2:** Examines both the design and opera6ng effec6veness of controls over a review period (for example, 6–12 months) 

SOC 2 framework is not prescrip6ve. It provides criteria but not a fixed control list, offering organiza6ons the flexibility to design controls suited to their environment—especially relevant in dynamic cloud contexts such as AWS. 

For official references, see <u>AICPA Trust Services Criteria and SOC 2 Resources.</u> 

# Understanding the SOC 2 framework 

The SOC 2 framework is built on the Commihee of Sponsoring Organiza6ons of the Treadway Commission (COSO) Internal Control Framework, which outlines five components of internal controls. The AICPA TSC (TSC 2017) adopts these principles and organizes them into: 



Page 2 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Common criteria for security (CC1 to CC9) 

   - These apply to all SOC 2 audits, regardless of which TSC are in scope 

   - Address control areas like governance, risk assessment, access control, system opera6ons, and monitoring 

- Category-specific criteria (Addi6onal criteria apply only if the organiza6on includes that category in its SOC 2 scope): 

   - PI1 (Processing Integrity) 

   - A1 (Availability) 

   - C1 (Confiden6ality) 

   - P1–P8 (Privacy) 

#### **Each criterion includes:** 

- **A control objec:ve** : What must be achieved 

- **A list of points of focus** : Suggested elements that a well-designed control might include 

#### **Auditors assess:** 

- **Design effec:veness** : Is the control likely to meet the objec6ve? 

- **Opera:onal effec:veness (Type 2 only)** : Did it operate consistently during the review period? 

The TSC framework can be reviewed in detail using AICPA criteria documenta6on. 

Figure 1 maps SOC 2’s Trust Services Criteria—Security, Availability, Processing Integrity, Confiden6ality, and Privacy—to the COSO framework, showing how internal controls are layered within the organiza6on’s governance and risk environment, in line with AICPA’s principle-based approach. 



Page 3 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 



<!-- Start of picture text -->
:9 »y E=aN<br>n z=.<br><!-- End of picture text -->

_Figure 1: SOC2 TSC and COSO internal control framework_ 

# SOC 2 in AWS context 

In cloud environments like AWS, implemen6ng SOC 2 controls requires interpre6ng the TSC within the _shared responsibility model_ : 

- **AWS** is responsible for the security _of_ the cloud (for example, the data center, hardware, and network infrastructure) 

- **Customers** are responsible for the security _in_ the cloud (for example, iden6ty management, data encryp6on, logging, and network controls) 

This division makes it cri6cal that customers: 

- Understand which SOC 2 TSC AWS helps address 

- Know what remains their responsibility 

- Design controls that use AWS services, such as AWS Iden6ty and Access Management <u>(IAM), AWS Key Management Service (AWS KMS), AWS Config, and AWS CloudTrail</u> 

- Document and monitor those controls to demonstrate effec6veness 

The flexibility of SOC 2 means each organiza6on must define its own control set. This whitepaper helps translate SOC 2 criteria into ac6onable customer controls using AWS services and governance structures, aligning technical opera6ons with audit expecta6ons. 



<!-- Start of picture text -->
aws<br>—<br><!-- End of picture text -->

Page 4 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

While AWS provides a secure and compliance-aligned founda6on, organiza6ons remain responsible for implemen6ng all controls within their own AWS environment—this includes how workloads are architected, how iden66es are managed, how data is protected, and how governance is enforced. 

This whitepaper provides prac6cal guidance on how customers can implement controls _in the cloud_ , specifically within the scope of their AWS accounts, services, and infrastructure. By interpre6ng each SOC 2 Trust Services Criterion through the lens of the AWS shared responsibility model, we help customers bridge control expecta6ons with prac6cal implementa6on steps. 

The following sec6ons walk through each SOC2 control criterion, offering prac6cal insight into: 

- How customers can interpret and apply each criterion within their AWS environment by iden6fying controls that align with the TSC and related points of focus 

- Which AWS services support compliance 

- What configura6on decisions must be made 

- What remains the customer’s responsibility (for example, policies, processes, and reviews). 



Page 5 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

# AWS Shared Responsibility model and its role in SOC 2 

The AWS Share Responsibility Model states that "Security and compliance is a shared responsibility between AWS and the customer. This shared model can help relieve the customer's opera6onal burden as AWS operates, manages, and controls the components from the host opera6ng system and virtualiza6on layer down to the physical security of the facili6es in which the service operates. Customers are responsible for managing the guest opera6ng system (including updates and security patches), other associated applica6on somware, as well as the configura6on of the AWS-provided security group firewall." 

In the context of customer SOC 2 assessments, this shared responsibility model clarifies which control objec6ves can be inherited from AWS and which must be implemented by the customer directly within their cloud workloads. AWS provides secure infrastructure and services, but the customer is accountable for how those services are configured, used, and monitored. 

- AWS is responsible for the physical security of its data centers and the isola6on of customer environments through hypervisor-level controls. These measures support CC6.4 (logical and physical access controls at the infrastructure level) by helping to prevent unauthorized physical or virtual access to customer workloads. 

- Customers are responsible for implemen6ng tenant-level controls, such as IAM role design (CC6.1), KMS policy enforcement (CC5.2), backup strategies, and logging configura6ons (CC7.x), to sa6sfy their part of the SOC 2 requirements. 

**Note:** Specific control mappings, responsibili6es, and implementa6on ac6ons are provided in the subsequent sec6ons and detailed tables. 

By understanding this delinea6on, customers can effec6vely scope, implement, and document their own controls that sa6sfy SOC 2 requirements while using the built-in assurances provided by the AWS compliance program. 

For more details, see the AICPA SOC 2 Resource Library and AWS Compliance Center. 

Customers can refer to AWS Prescrip6ve Guidance to design and implement controls appropriate for their specific environment and compliance needs. These resources provide strategies and paherns that align with AWS best prac6ces and can help organiza6ons opera6onalize their SOC 2 responsibili6es more effec6vely. When used in conjunc6on with the 



Page 6 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

<u>AWS Shared Responsibility Model, this guidance enables customers to architect, configure, and</u> validate controls across security, availability, and privacy domains. 

The boundaries of responsibili6es between AWS and the customer can vary depending on the AWS services selected. Customers can assess each service opera6onal model and understand how responsibili6es shim accordingly. 

## **Complementary User En0ty Controls: Customer responsibili0es in the cloud** 

Complementary User En6ty Controls (CUECs) are control ac6vi6es that a service provider expects its customers (user en66es) to implement for the provider’s controls to func6on effec6vely. These controls are disclosed in the service provider’s SOC 2 report, not as part of the TSC, but as required contextual disclosures under the AICPA SOC 2 repor6ng framework. 

CUECs are not op6onal. If the customer fails to implement these controls, the effec6veness of the overall system might be compromised—even if the provider’s controls are working as intended. 

## **CUECs and the Shared Responsibility Model** 

In the context of AWS, the Shared Responsibility Model defines which controls AWS manages (for example, infrastructure security, physical access, and hypervisors) and which controls customers must implement (for example, access management, data protec6on, and monitoring). 

AWS discloses CUECs in its SOC 2 Type II report to communicate the expecta6ons placed on customers. These typically include areas such as: 

- Managing IAM roles and permissions 

- Encryp6ng and backing up data 

- Reviewing logs and responding to security alerts 

- Securing user devices that access AWS services 

Thus, CUECs reflect the customer-side of the shared responsibility model, reinforcing the areas that must be addressed by the customer for a secure and compliance-aligned AWS implementa6on. 



Page 7 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

Organiza6ons pursuing SOC 2 for workloads running on AWS should: 

1. Review the CUECs disclosed in the AWS SOC 2 report 

2. Map those CUECs to their own internal control ac6vi6es 

3. Implement suppor6ng policies, procedures, and technical configura6ons 

4. Provide evidence (for example, IAM policies, backup jobs, and incident response logs) that these controls are opera6ng effec6vely 

Figure 2 Shows how SOC 2 TSC, the AWS Shared Responsibility Model, and Complementary User En6ty Controls (CUECs) interrelate in the context of a customer's SOC 2 audit. The customer implements the controls needed to support AWS controls (CUECs). The CUECs feed into the Shared Responsibility Model, which defines who is responsible for each of the TSC. 



<!-- Start of picture text -->
AICPA Trust Service Criteria<br>Security, Availability, Confidentiality, and so on<br>AWS responsibilities Customer responsibilities<br>Infrastructure, data centers, IAM, backup, logging, and<br>network, and so on monitoring<br>Complimentary User Entity Controls<br>Controls customer must implementto supportAWS controls<br><!-- End of picture text -->

_Figure 2: The relaDonship of the CUEC, AWS Shared Responsibility Model, and TSC_ 



<!-- Start of picture text -->
—7<br><!-- End of picture text -->

Page 8 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

# Applying SOC 2 TSC in AWS environments 

The SOC 2 framework defines a series of control criteria that service organiza6ons must meet to demonstrate effec6ve system design and opera6onal performance aligned with the TSC. These criteria include both the founda6onal Common Criteria for Security category (CC1–CC9) and the Category-Specific Criteria for Availability, Processing Integrity, Confiden6ality, and Privacy. 

Understanding the boundary between AWS and the customer, defined by the AWS Shared Responsibility Model, is only the star6ng point. This model dis6nguishes which security and compliance responsibili6es are managed by AWS (for example, infrastructure, hardware, and physical access) and which are managed by the customer (for example, data protec6on, IAM, and workload configura6ons). 

The next step is to translate SOC 2’s principle-based and high-level control criteria into specific, ac6onable responsibili6es, technical implementa6ons, and suppor6ng evidence within the customer’s AWS environment. 

This control mapping sec6on provides prac6cal implementa6on guidance to help customers: 

- Interpret each SOC 2 control criterion within the context of their AWS environment 

- Implement technical controls using AWS services and secure configura6ons 

- Define suppor6ng organiza6onal policies, procedures, and governance ac6vi6es outside of AWS 

- Use the publicly available points of focus as interpre6ve aids to guide control implementa6on and evidence collec6on 

Each of the following sec6ons outlines: 

- A short narra6ve explaining the purpose of each control area 

- Prac6cal AWS service recommenda6ons to support compliance 

- Tables that describe SOC 2 control objec6ves, customer responsibili6es in AWS, external controls, and associated points of focus. 

This structured approach helps cloud-focused organiza6ons bridge the gap between high-level SOC 2 expecta6ons and prac6cal, verifiable implementa6on within their AWS environments— suppor6ng both opera6onal maturity and audit readiness. 



Page 9 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

**Note:** Many technical and procedural controls can sa6sfy mul6ple SOC 2 TSC. For example, a well-configured logging and monitoring solu6on can address requirements under both Security (CC7.x) and Availability (A1.x). Customers are encouraged to iden6fy opportuni6es to reuse and align controls across criteria, reducing redundancy and improving audit efficiency. Clear documenta6on and traceability of such control mappings are essen6al for demonstra6ng compliance coverage. 

## **CC1 series: Control Environment** 

The Control Environment (CC1 series) criteria establish the overall founda6on for an effec6ve system of internal control, as defined in the AICPA 2017 TSC. 

These criteria help ensure that the en6ty demonstrates commitment to integrity and ethical values, establishes appropriate governance and oversight structures, defines clear roles and responsibili6es, ahracts and retains competent individuals, and holds individuals accountable for their internal control responsibili6es. 

In AWS-hosted environments, such as cloud-focused applica6ons, serverless workloads, or regulated financial services products, the control environment remains the customer's responsibility. 

AWS provides tools and services that can support the enforcement, monitoring, and audi6ng of control ac6vi6es (for example, IAM, CloudTrail, AWS Config, AWS Organiza6ons service control policies (SCPs), and ahribute-based access control (ABAC) policies), but organiza6onal leadership, governance, people management, policies, and accountability structures are en6rely owned and operated by the customer. 

Customers are responsible for configuring AWS security and access controls (IAM, Organiza6ons SCP, and AWS Config) in line with their organiza6onal policies and for helping to ensure that these configura6ons are 6ed into broader internal control structures, accountability models, and governance repor6ng mechanisms. 

When aligning with the SOC 2 TSC, organiza6ons should use the points of focus as interpre6ve guidance to assess the completeness and effec6veness of their control implementa6on. While the points of focus are not mandatory or prescrip6ve checklists, they provide useful context for demonstra6ng how specific criteria are met. 



Page 10 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**CC1.1: The en:ty**<br>**demonstrates a commitment**<br>**to integrity and ethical**<br>**values.**|• Considers contractors and<br>vendor employees in<br>demonstra6ng its<br>commitment|• To demonstrate AWS<br>commitment, obtain<br>third-party ahesta6on<br>reports from AWS Ar6fact|
|**CC1.2: The board of directors**<br>**demonstrates independence**<br>**from management and**<br>**exercises oversight of the**<br>**development and**<br>**performance of internal**<br>**control.**|• Not applicable|• No AWS specific<br>implementa6on|
|**CC1.3: Management**<br>**establishes, with board**<br>**oversight, structures,**<br>**repor:ng lines, and**<br>**appropriate authori:es and**<br>**responsibili:es in the pursuit**<br>**of objec:ves.**|• Defines, assigns, and<br>limits authori6es and<br>responsibili6es|• To address strict<br>segrega6on of du6es,<br>implement IAM and AWS<br>IAM Iden6ty Center role-<br>based access control<br>(RBAC) and resource<br>access controls|
|**CC1.4: The en:ty**<br>**demonstrates a commitment**<br>**to aPract, develop, and**<br>**retain competent individuals**<br>**in alignment with objec:ves.**|• Provides training to<br>maintain technical<br>competencies|• To assess individual<br>technical competency,<br>use the AWS Cer6fica6on<br>and Training program|
|**CC1.5 The en:ty holds**<br>**individuals accountable for**<br>**their internal control**<br>**responsibili:es in the pursuit**<br>**of objec:ves.**|• Enforces accountability<br>through structures,<br>authori6es, and<br>responsibili6es|• To enforce individual<br>accountability, enable<br>logging with CloudTrail<br>and user ac6vity<br>monitoring with Amazon<br>CloudWatch|



#### **Non-AWS implemented controls (organiza:onal, process, and people):** 

- Make sure that the members of the board have the necessary AWS exper6se. 



Page 11 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Formalize an official organiza6on chart that encompasses AWS opera6ons. 

- Establish a process for annual performance reviews that incorporate AWS knowledge. 

## **CC2 series: Communica0on and Informa0on** 

The Communica6on and Informa6on (CC2 series) criteria require the en6ty to obtain, generate, use, and communicate relevant, quality informa6on internally and externally to enable effec6ve control opera6ons. 

This includes internal communica6on of objec6ves, responsibili6es, incident response processes, and system opera6ons, as well as communica6on with external par6es such as customers, vendors, and regulators. In the AWS context, customers are responsible for making sure that their cloud workloads (whether server- based, serverless, or hybrid) generate accurate logs, metrics, and event data, and that relevant system and security informa6on is captured, distributed, and communicated appropriately within their organiza6on and to third par6es as needed. 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**CC2.1: The en:ty obtains or**<br>**generates and uses relevant,**<br>**quality informa:on to**<br>**support the func:oning of**<br>**internal control.**|• Captures internal and<br>external sources of data<br>• Processes relevant data<br>into informa6on<br>• Maintains quality<br>throughput processing|• To capture system and<br>user ac6vi6es, enable<br>CloudTrail and AWS<br>service level logging<br>• To capture and log AWS<br>configura6on states,<br>enable the AWS Config<br>Recorder|
|||• To obtain ac6onable<br>informa6on, establish<br>relevant metrics in<br>CloudWatch for aler6ng<br>and enable AWS Config<br>Conformance Packs|





Page 12 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|||• To maintain the source<br>data quality, enable<br>CloudTrail log file<br>valida6on and log file<br>encryp6on, in addi6on to<br>Amazon Simple Storage<br>Service (Amazon S3)<br>bucket encryp6on|
|---|---|---|
|**CC2.2: The en:ty internally**<br>**communicates informa:on,**<br>**including objec:ves and**<br>**responsibili:es for internal**<br>**control, necessary to support**<br>**the func:oning of internal**<br>**control.**|• Communicates internal<br>control informa6on<br>• Communicates system<br>changes|• To properly no6fy<br>personnel of ac6onable<br>CloudWatch alarms or<br>system changes, create<br>specificAmazon Simple<br>No6fica6on Service<br>(Amazon SNS)topics for<br>informa6on distribu6on<br>using different<br>communica6on channels|
|**CC2.3: The en:ty**<br>**communicates with external**<br>**par:es regarding maPers**<br>**affec:ng the func:oning of**<br>**internal control.**|• Not applicable|• No AWS specific<br>implementa6on|



#### **Non-AWS implemented controls (organiza:onal, process, and people):** 

- Monitor system logs and events from AWS services and integrate into centralized monitoring tools (for example, SIEM). 

- Establish informa6on requirements for control opera6ons, incident response, and risk management over AWS opera6ons. 

- Define and communicate job responsibili6es and control objec6ves in AWS to relevant individuals in a 6mely manner. 

In addi6on to the controls implemented in or for AWS, it is important for the customer organiza6on to define responsibility for communica6on strategies, incident escala6on paths, 



Page 13 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

and customer no6fica6ons to make sure that system objec6ves and changes are effec6vely communicated internally and externally. 

## **CC3 series: Risk Assessment** 

The Risk Assessment (CC3 series) criteria require the en6ty to establish and implement processes for iden6fying, analyzing, and responding to risks that might affect the achievement of system objec6ves, including security, availability, processing integrity, confiden6ality, and privacy. 

This includes specifying system objec6ves, iden6fying and analyzing internal and external risks (including fraud risks), and assessing changes that could significantly affect internal control. 

In AWS-hosted environments, customers are responsible for conduc6ng regular risk assessments covering their cloud architecture, configura6ons, data flows, and dependencies, while considering threats specific to the cloud shared responsibility model, cloud-focused risks, third-party integra6ons, and service dependencies. 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**CC3.1: The en:ty specifies**<br>**objec:ves with sufficient**<br>**clarity to enable the**<br>**iden:fica:on and**<br>**assessment of risks rela:ng**<br>**to objec:ves.**|• Aligns with externally<br>established frameworks|• To use pre-built control<br>evalua6ons in compliance<br>frameworks, enable AWS<br>Config conformance<br>packs and AWS Security<br>Hub|
|**CC3.2: The en:ty iden:fies**<br>**risks to the achievement of**<br>**its objec:ves across the**<br>**en:ty and analyzes risks as a**<br>**basis for determining how**<br>**the risks should be**<br>**managed.**|• Iden6fies and assesses<br>cri6cality of informa6on<br>assets and iden6fies<br>threats and<br>vulnerabili6es|• To iden6fy system<br>vulnerabili6es, enable<br>Amazon Inspectorto scan<br>for vulnerabili6es in<br>Amazon Elas6c Compute<br>Cloud (Amazon EC2),<br>Amazon Elas6c Container<br>Registry (Amazon ECR),<br>andAWS Lambda|





Page 14 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|||• For threat detec6on,<br>enableAmazon<br>GuardDutyto monitor<br>AWS accounts and<br>workloads for malicious<br>ac6vi6es|
|---|---|---|
|**CC3.3: The en:ty considers**<br>**the poten:al for fraud in**<br>**assessing risks to the**<br>**achievement of objec:ves.**|• Considers the risks<br>related to the use of IT<br>and access to informa6on|• To evaluate least-privilege<br>access to informa6on,<br>enableAWS IAM Access<br>Analyzer to track unused<br>access and permissions in<br>AWS accounts|
|**CC3.4: The en:ty iden:fies**<br>**and assesses changes that**<br>**could significantly impact**<br>**the system of internal**<br>**control.**|• Assesses changes in<br>systems and technology|• To accurately track<br>changes, enableAWS<br>CloudForma6on drim<br>detec6on for<br>infrastructure as code<br>(IaS), AWS Config rules<br>for AWS configura6on,<br>and CloudTrail for API-<br>ini6ated changes|



#### **Non-AWS Implemented controls (organiza:onal, process, and people):** 

- Define system objec6ves for AWS workloads aligned with contracts, regulatory obliga6ons, and organiza6onal strategy 

- Subscribe threat intelligent on all services used on AWS 

- Evaluate risk impacts and risk opportuni6es specific to opera6ons in AWS 

In addi6on to the controls implemented in or for AWS, it is important for the customer organiza6on to define ownership of the risk management framework, methodology, priori6za6on, and risk treatment. 



Page 15 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

## **CC4 series: Monitoring Ac0vi0es** 

The Monitoring Ac6vi6es (CC4 series) criteria require the en6ty to select, develop, and perform ongoing or separate evalua6ons to determine whether components of internal control are present and func6oning and to evaluate and communicate deficiencies to the par6es responsible for correc6ve ac6on. This includes con6nuous monitoring of systems, configura6ons, security events, and control effec6veness, as well as the 6mely iden6fica6on and remedia6on of control deficiencies. 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**CC4.1: The en:ty selects,**<br>**develops, and performs**<br>**ongoing and/or separate**<br>**evalua:ons to ascertain**<br>**whether the components of**<br>**internal control are present**<br>**and func:oning.**|• Mix of ongoing and<br>separate evalua6ons.<br>• Establishes baseline<br>understanding|• To iden6fy system<br>vulnerabili6es, enable<br>Amazon Inspector to<br>scan for vulnerabili6es<br>in Amazon EC2,<br>Amazon ECR, and<br>Lambda<br>• To con6nuously<br>evaluate AWS<br>resource<br>configura6on against<br>a baseline and enable<br>AWS Config<br>conformance packs|
|**CC4.2: The en:ty evaluates**<br>**and communicates internal**<br>**control deficiencies in a**<br>**:mely manner to those**<br>**par:es responsible for taking**<br>**correc:ve ac:on, including**<br>**senior management and the**<br>**board of directors, as**<br>**appropriate.**|• Communicates<br>deficiencies.<br>• Monitors correc6ve<br>ac6on|• To properly no6fy<br>personnel of security<br>findings, create<br>specific Amazon SNS<br>topics for informa6on<br>distribu6on using<br>different<br>communica6on<br>channels|





Page 16 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- To centralize, monitor, and track security issues and resolu6ons, enable Security Hub to accept findings from both AWS and nonAWS security tools 

#### **Non-AWS implemented controls (organiza:onal, process, and people):** 

- Establish security baselines for different AWS workloads. 

- Define evalua6on scope and frequency for AWS workloads and opera6ons based on iden6fied risks. 

- Formalize ownership of AWS accounts and workloads for correc6ve ac6ons. 

- Document processes for penetra6on tes6ng, red teaming, and independent assessments on AWS. 

AWS does not perform governance reviews, audits, or human-in-the-loop valida6ons on behalf of customers. Therefore, customers are fully responsible for establishing and opera6ng their monitoring programs, controlling effec6veness reviews, and implemen6ng remedia6on processes. 

## **CC5 series: Control Ac0vi0es** 

The Control Ac6vi6es (CC5 series) criteria require the en6ty to select and develop control ac6vi6es that contribute to the mi6ga6on of risks to the achievement of system objec6ves, implement general IT controls (ITGC), and deploy controls through policies and procedures. These controls help ensure that risks iden6fied during the risk assessment process are effec6vely mi6gated through opera6onal, technical, and procedural safeguards. 

In AWS-hosted environments, customers are responsible for designing, implemen6ng, and enforcing control ac6vi6es over cloud configura6ons, deployments, data access, processing, change management, and security monitoring. AWS supports these ac6vi6es by providing configurable security and opera6onal services. 



Page 17 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**CC5.1: The en:ty selects and**<br>**develops control ac:vi:es**<br>**that contribute to the**<br>**mi:ga:on of risks to the**<br>**achievement of objec:ves to**<br>**acceptable levels.**|• Addresses segrega6on of<br>du6es|• To address strict<br>segrega6on of du6es,<br>implement IAM and IAM<br>Iden6ty Center RBAC and<br>resource access controls|
|**CC5.2: The en:ty also selects**<br>**and develops general control**<br>**ac:vi:es over technology to**<br>**support the achievement of**<br>**objec:ves.**|• Establishes relevant<br>technology infrastructure<br>control ac6vi6es<br>• Establishes relevant<br>security management<br>process controls ac6vi6es|• To help ensure the<br>completeness, accuracy,<br>and availability of<br>technology processing,<br>enable Security Hub to<br>accept findings from both<br>AWS and non-AWS<br>security tools<br>• To restrict technology<br>access rights, enable IAM<br>Access Analyzer to track<br>unused access and<br>permissions in AWS<br>accounts|
|**CC5.3: The en:ty deploys**<br>**control ac:vi:es through**<br>**policies that establish what**<br>**is expected and in**<br>**procedures that put policies**<br>**into ac:on.**|• Performs in a 6mely<br>manner<br>• Takes correc6ve ac6on|• To perform control<br>ac6vi6es in a 6mely<br>manner, enable AWS<br>Config Rules to automate<br>evalua6on of system<br>controls|





Page 18 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- To help ensure correc6ve ac6on is automa6cally completed, configure AWS Config rules to include remedia6on ac6on 

#### **Non-AWS implemented controls (organiza:onal, process, and people):** 

- Determine controls ac6vi6es at various levels in AWS regarding the Shared Responsibility Matrix. 

- Evaluate the dependency between AWS technical controls and business process controls. 

- Establish policies and procedures that govern both automated and manual controls implemented in AWS. 

While AWS provides tools, customers retain full responsibility for defining control ac6vi6es, implemen6ng them in their AWS accounts, and making sure that they are enforced consistently using policies, procedures, and governance processes. 

## **CC6 series: Logical and Physical Access Controls** 

The Logical and Physical Access Controls (CC6 series) criteria require the en6ty to implement controls to restrict logical and physical access to systems, data, and facili6es, making sure that only authorized individuals are granted appropriate access and that access is revoked when no longer required. 

This also includes controls over remote access, transmission, movement, removal of informa6on, and protec6ons against unauthorized or malicious somware. 

In AWS environments, customers are responsible for managing logical access to their AWS accounts, services, data, and applica6ons. 

**SOC 2 TSC iden:fier Points of focus covered Customer responsibili:es (AWS specific implementa:on)** 



Page 19 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- To track AWS resources 

- **CC6.1: The en:ty** • Iden6fies and manages **implements logical access** the inventory of and EC2 instances, enable **security soZware,** informa6on assets AWS Config configura6on 

- **infrastructure, and** recorder and AWS **architectures over protected** • Restricts logical access <u>Systems Manager</u> 

- **informa:on assets to protect** • Considers network Inventory 

- **them from security events to meet the en:ty's objec:ves.** segmenta6on • To restrict logical access 

- • Restricts access to to informa6on assets informa6on assets based on specific requirements, configure 

- • Manages creden6als for RBAC using IAM and IAM 

- infrastructure and Iden6ty Center and 

- somware access controls with 

- • Uses encryp6on to SCPs), resource control protect data policies (RCPs), and resource based policies 

- • Protects encryp6on keys such as S3 bucket policies 

- • To isolate network environments, use mul6ple AWS accounts, mul6ple Amazon Virtual Private Clouds (Amazon VPCs), and restrict traffic using security groups and network access control lists (network ACLs) 

- • To protect authen6ca6on data, store creden6als in <u>AWS Secrets Manager or</u> Systems Manager Parameter Store 



Page 20 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

• To protect data at rest, enable AWS KMS encryp6on on Amazon storage services, such as <u>Amazon Elas6c Block Store (Amazon EBS),</u> Amazon S3, and so on • To protect encryp6on keys during genera6on, storage, use, and destruc6on, use AWS KMS customer managed keys **CC6.2: Prior to issuing** • Reviews appropriateness • To track usage and **system creden:als and** of access creden6als informa6on on access **gran:ng system access, the** creden6als, enable IAM **en:ty registers and** Access Analyzer and IAM **authorizes new internal and** creden6al reports **external users whose access is administered by the en:ty. For those users whose access is administered by the en:ty, user system creden:als are removed when user access is no longer authorized. CC6.3: The en:ty authorizes,** • Uses role-based access • To segregate **modifies, or removes access** controls incompa6ble func6ons, **to data, soZware, func:ons,** implement IAM and IAM **and other protected** Iden6ty Center RBAC and **informa:on assets based on** resource access controls **roles, responsibili:es, or the system design and changes, giving con-sidera:on to the concepts of least privilege and segrega:on of du:es, to meet the en:ty’s objec:ves.** 



Page 21 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**CC6.4: The en:ty restricts**<br>**physical access to facili:es**<br>**and protected informa:on**<br>**assets (for example, data**<br>**center facili:es, backup**<br>**media storage, and other**<br>**sensi:ve loca:ons) to**<br>**authorized personnel to**<br>**meet the en:ty’s objec:ves.**|• Not applicable|• AWS is responsible for<br>physical access to the<br>facili6es that are hosted<br>on AWS services|
|---|---|---|
|**CC6.5: The en:ty**<br>**discon:nues logical and**<br>**physical protec:ons over**<br>**physical assets only aZer the**<br>**ability to read or recover**<br>**data and soZware from**<br>**those assets has been**<br>**diminished and is no longer**<br>**required to meet the en:ty’s**<br>**objec:ves.**|• Not applicable|• AWS is responsible for the<br>physical assets of the<br>facili6es that are hosted<br>on AWS services|
|**CC6.6: The en:ty**<br>**implements logical access**<br>**security measures to protect**<br>**against threats from sources**<br>**outside its system**<br>**boundaries.**|• Restricts access<br>• Requires addi6onal<br>authen6ca6on or<br>creden6als<br>• Implements boundary<br>protec6on systems|• To restrict communica6on<br>channels, use mul6ple<br>AWS accounts, mul6ple<br>Amazon VPCs, and<br>restrict traffic using<br>security groups and<br>network ACLs<br>• To incorporate addi6onal<br>authen6ca6on<br>informa6on, enable<br>mul6factor<br>authen6ca6on (MFA) in<br>IAM and IAM Iden6ty<br>Center|





Page 22 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|||• To detect external access<br>ahempts, enable<br>GuardDuty to alert on<br>ac6vi6es that show<br>abnormal behavior|
|---|---|---|
|**CC6.7: The en:ty restricts**<br>**the transmission,**<br>**movement, and removal of**<br>**informa:on to authorized**<br>**internal and external users**<br>**and processes, and protects**<br>**it during transmission,**<br>**movement, or removal to**<br>**meet the en:ty’s objec:ves.**|• Uses encryp6on<br>technologies or secure<br>communica6on channels<br>to protect data|• To protect transmission of<br>data, use SSL cer6ficates<br>stored in AWS Cer6ficate<br>Manager (ACM)and AWS<br>PrivateLink, such as VPC<br>endpoints, to securely<br>connect with AWS<br>services|
|**CC6.8: The en:ty**<br>**implements controls to**<br>**prevent or detect and act**<br>**upon the introduc:on of**<br>**unauthorized or malicious**<br>**soZware to meet the en:ty’s**<br>**objec:ves.**|• Restricts applica6on and<br>somware installa6on<br>• Detects unauthorized<br>changes to somware and<br>configura6on parameters<br>• Uses an6virus and an6-<br>malware somware|• To restrict the ability to<br>install applica6on and<br>somware, enable SCPs<br>and configureAWS<br>Service Catalog<br>• To detect changes to<br>somware and<br>configura6on, enable<br>CloudForma6on drim<br>detec6on for IaS, AWS<br>Config rules for AWS<br>configura6on, and<br>CloudTrail for API-<br>ini6ated changes<br>• To detect and remediate<br>viruses, enable<br>GuardDuty Malware<br>Protec6on for EC2andS3|



**Non-AWS implemented controls (organiza:onal, process, and people):** 



Page 23 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Establish a formal process for logical access provisioning, removal, and review for AWS infrastructure and applica6ons. 

- See the AWS third-party ahesta6on for physical access controls around AWS hosted infrastructure. 

Physical access controls for AWS infrastructure are managed by AWS and are evaluated as part of the AWS SOC 2 Type II report, which covers physical data center security (for example, badge access, video surveillance, and security guards). Customers can inherit these controls when using AWS infrastructure to demonstrate compliance with relevant criteria, such as CC6.4. 

However, under the shared responsibility model, customers remain accountable for managing physical access to any components outside of AWS infrastructure—such as their own corporate offices, on-premises data centers, employee laptops, or other user devices that connect to AWS resources. These areas must be included in the customer’s SOC 2 assessment if they impact the confiden6ality, integrity, or availability of customer data or systems. 

Addi6onal implementa6on guidance on physical access responsibili6es and how they map to SOC 2 criteria (for example, CC6.4 and CC6.5) is provided in the control mapping tables later in this document. 

## **CC7 series: System Opera0ons** 

The System Opera6ons (CC7 series) criteria require the en6ty to design and operate ac6vi6es to manage system opera6ons, detect and monitor devia6ons from expected performance, and respond to and recover from security incidents and system failures in a controlled manner. 

This includes configura6on monitoring, anomaly detec6on, event analysis, incident response, and recovery from disrup6ons. 

In AWS-hosted environments, customers can use a suite of AWS services to enable automated, real-6me monitoring, event-driven detec6on, and response automa6on. 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**i**|
|---|---|---|
|||**(AWS specific**|
|||**implementa:on)**|





Page 24 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**CC7.1: To meet its objec:ves,**<br>**the en:ty uses detec:on and**<br>**monitoring procedures to**<br>**iden:fy (1) changes to**<br>**configura:ons that result in**<br>**the introduc:on of new**<br>**vulnerabili:es, and (2)**<br>**suscep:bili:es to newly**<br>**discovered vulnerabili:es.**|• Monitors infrastructure<br>and somware<br>• Implements change-<br>detec6on mechanisms<br>• Detects unknown or<br>unauthorized<br>components<br>• Conducts vulnerability<br>scans|• To alert personnel to<br>unauthorized<br>modifica6ons of cri6cal<br>system files,<br>configura6on files, or<br>content files, enable<br>CloudForma6on drim<br>detec6on for IaS, AWS<br>Config rules for AWS<br>configura6on, and<br>CloudTrail for API-<br>ini6ated changes<br>• To iden6fy poten6al<br>vulnerabili6es, enable<br>Amazon Inspector to scan<br>for vulnerabili6es in<br>Amazon EC2, Amazon<br>ECR, and Lambda|
|---|---|---|
|**CC7.2: The en:ty monitors**<br>**system components and the**<br>**opera:on of those**<br>**components for anomalies**<br>**that are indica:ve of**<br>**malicious acts, natural**<br>**disasters, and errors**<br>**affec:ng the en:ty's ability**<br>**to meet its objec:ves;**<br>**anomalies are analyzed to**<br>**determine whether they**<br>**represent security events.**|• Implements filters to<br>analyze anomalies|• To filter, summarize, and<br>analyze anomalies using<br>machine learning<br>techniques, enable<br>GuardDuty|





Page 25 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**CC7.3: The en:ty evaluates**<br>**security events to determine**<br>**whether they could or have**<br>**resulted in a failure of the**<br>**en:ty to meet its objec:ves**<br>**(security incidents) and, if**<br>**so, takes ac:ons to prevent**<br>**or address such failures.**|• Communicates and<br>reviews detected security<br>events|• To properly no6fy<br>personnel of security<br>events, create specific<br>Amazon SNS topics for<br>informa6on distribu6on<br>using different<br>communica6on channels|
|---|---|---|
|**CC7.4: The en:ty responds**<br>**to iden:fied security**<br>**incidents by execu:ng a**<br>**defined incident-response**<br>**program to understand,**<br>**contain, remediate, and**<br>**communicate security**<br>**incidents, as appropriate.**|• Contains security<br>incidents<br>• Mi6gates ongoing<br>security incidents<br>• Develops and implements<br>communica6on protocols<br>for security incidents|• To contain, mi6gate, and<br>communicate ac6ve<br>security incidents,<br>configure Incident<br>Manager, a capability of<br>AWS Systems Manager<br>Incident Manager, with<br>customized responses<br>plans and runbooks|
|**CC7.5: The en:ty iden:fies,**<br>**develops, and implements**<br>**ac:vi:es to recover from**<br>**iden:fied security incidents.**|• Improves response and<br>recovery procedures|• To improve the incident<br>response process, use<br>Incident Manager to<br>collect informa6on to<br>diagnose and learn from<br>incidents|



#### **Non-AWS implemented controls (organiza:onal, process, and people):** 

- Define baseline configura6ons and golden Amazon Machine Images (AMIs) in AWS. 

- Establish formal processes and runbooks for incident response in AWS. 

- Conduct periodic automated and manual incident response tes6ng for AWS services. 

While AWS provides the infrastructure and tools for opera6onal excellence and incident handling, the customer is fully responsible for defining, implemen6ng, and opera6ng the incident response plan, system monitoring strategy, and recovery procedures tailored to their business and compliance requirements. 



Page 26 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

## **CC8 series: Change Management** 

The Change Management (CC8 series) criteria require the en6ty to implement a formal change management process to make sure that changes to infrastructure, data, somware, and procedures are authorized, tested, documented, and properly implemented. 

This helps reduce the risk of unauthorized, ineffec6ve, or uncontrolled changes impac6ng system security, availability, processing integrity, confiden6ality, and privacy. 

In AWS-hosted environments, customers are responsible for managing changes to their cloud resources, configura6ons, and services. AWS provides services to help automate, manage, and control changes securely and at scale. 

|**SOC 2 TSC iden:fier**|**Points of focus Covered**|**Customer Responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**CC8.1: The en:ty authorizes,**<br>**designs, develops or**<br>**acquires, configures,**<br>**documents, tests, approves,**<br>**and implements changes to**<br>**infrastructure, data,**<br>**soZware, and procedures to**<br>**meet its objec:ves.**|• Manages changes<br>throughout the system<br>lifecycle<br>• Tracks system changes<br>• Tests system changes<br>• Approves system changes<br>• Deploys system changes<br>• Creates baseline<br>configura6on of IT<br>technology|• To automate change<br>process, use Change<br>Manager, a capability of<br>AWS Systems Manager<br>• To use somware<br>development lifecycle<br>controls for infrastructure<br>changes, implement<br>CloudForma6on for IaC<br>• To standardize code<br>change requirements for<br>tes6ng, approval, and<br>deployment, implement<br>AWS CodePipeline and<br>AWS Developer Tools|
|||• To maintain baseline<br>configura6on, use<br>Amazon EC2 Image<br>Builder to update golden<br>AMIs|





Page 27 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

#### **Non-AWS implemented controls (organiza:onal, process, and people):** 

- Define baseline configura6ons and golden AMIs in AWS. 

- Establish processes for emergency changes in AWS. 

While AWS supports secure change management through these services, the en6ty is responsible for defining change management policies, workflows, risk assessments, approvals, tes6ng, rollback procedures, and verifying change governance adherence across their environment. 

## **CC9 series: Risk Mi0ga0on** 

The Risk Mi6ga6on (CC9 series) criteria require the en6ty to iden6fy, select, and develop risk mi6ga6on ac6vi6es for risks arising from business disrup6ons and use of vendors and business partners. 

This helps ensure that the en6ty is prepared to handle incidents that could affect system objec6ves and that third-party risks are appropriately managed. 

In AWS-hosted environments, the en6ty remains responsible for managing their risk posture, including business con6nuity planning (BCP), disaster recovery (DR), third-party risk management, and vendor oversight. AWS provides tools and services that can support technical resilience, business con6nuity, and visibility into cloud vendor dependencies. 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**CC9.1: The en:ty iden:fies,**<br>**selects, and develops risk**<br>**mi:ga:on ac:vi:es for risks**<br>**arising from poten:al**<br>**business disrup:ons.**|• Considers mi6ga6on of<br>risks of business<br>disrup6on|• To limit the impact of<br>security event<br>disrup6ons, implement<br>mul6-Availability Zone<br>(AZ) and mul6-AWS<br>Region architectures and<br>use AWS Backup and AWS<br>Elas6c Disaster Recovery<br>backups to recover from<br>poten6al disrup6ons|





Page 28 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**CC9.2: The en:ty assesses**|• Assesses vendor and|• To demonstrate AWS|
|---|---|---|
|**and manages risks**|partner business risks|commitment, obtain|
|**associated with vendors and**||third-party ahesta6on|
|**business partners.**||reports from AWS Ar6fact|



#### **Non-AWS implemented controls (organiza:onal, process, and people):** 

- Conduct business impact analysis (BIA) on AWS workloads to verify that the AWS architecture supports the workloads. 

- Update the alternate security contact across AWS accounts for 6mely security no6fica6ons. 

Other processes, including vendor risk management programs, BCP and DR governance, tabletop exercises, and formal risk acceptance remain fully the customer's responsibility. 

While the Common Criteria (CC1–CC9) of SOC 2 apply universally to all trust categories, Category-Specific Criteria expand the control scope when a service organiza6on includes addi6onal commitments related to system Availability, Processing Integrity, Confiden6ality, or Privacy. 

Each of these categories introduces its own control objec6ves and points of focus that require focused implementa6on and valida6on. In AWS environments, mee6ng these extended requirements involves both technical configura6ons and suppor6ng organiza6onal governance. This includes: 

- Architec6ng workloads for resilience, con6nuity, and integrity 

- Applying controls for data protec6on, consent management, and privacy transparency 

- Using AWS services for enforcement, monitoring, and evidence genera6on 

These mappings provide prescrip6ve guidance for how customers can: 

- Interpret each SOC 2 category-specific criterion in the context of AWS 

- Iden6fy and configure AWS services that directly support compliance objec6ves 

- Design non-technical controls such as policies, training, and documented procedures 

- Align their environment to AICPA-defined points of focus used in SOC 2 audits 



Page 29 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

This structured approach enables organiza6ons to translate SOC 2 principles into clear, opera6onal ac6ons in the cloud—suppor6ng both audit readiness and real-world risk mi6ga6on. 

# Category specific criteria and AWS guidance 

In SOC 2 (TSC 2017), the Category-Specific Criteria (Availability, Processing Integrity, Confiden6ality, and Privacy) extend the Common Criteria (CC1–CC9) by focusing on controls that address the specific objec6ves commihed by the service organiza6on to its customers or regulators. 

These categories are scoped into a SOC 2 examina6on when the organiza6on asserts commitments around system up6me, data processing accuracy, informa6on confiden6ality, or personal data privacy. 

While AWS provides a highly resilient, secure, and globally available cloud environment, customers are responsible for configuring AWS services appropriately, implemen6ng controls within their AWS environment, and managing suppor6ng organiza6onal policies, processes, and governance frameworks to meet these criteria. 

This whitepaper provides prescrip6ve guidance for customers to: 

- Use AWS services (for example, CloudWatch, AWS Config, Amazon Inspector, AWS KMS, <u>Amazon Macie, AWS Backup, and Elas6c Disaster Recovery) to implement technical</u> controls suppor6ng SOC 2 category-specific objec6ves 

- Understand the AWS shared responsibility model boundaries for each category 

- Design and operate necessary organiza6onal controls and governance to supplement AWS technical capabili6es 

This guidance enables customers to align their AWS-based workloads and services with the SOC 2 TSC 2017 category-specific requirements effec6vely. 

## **PI series: Processing Integrity** 

The Processing Integrity (PI series) criteria in SOC 2 TSC 2017 focus on making sure that system processing is complete, valid, accurate, 6mely, and authorized to meet the en6ty's commitments and objec6ves. 



Page 30 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

These criteria require controls over data inputs, processing, outputs, and storage to help ensure that data is handled appropriately throughout its lifecycle and that errors or devia6ons are iden6fied and corrected promptly. 

In AWS-hosted environments, while AWS provides services that support data processing (for example, compute, storage, database services), the customer retains full responsibility for making sure of the correctness, integrity, and accuracy of data and processes within their applica6ons and workflows. 

Customers should implement data valida6on checks, processing logs, monitoring mechanisms, and reconcilia6on controls, using AWS services combined with strong governance, documented processing procedures, and error-handling protocols. 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**<br>i|
|---|---|---|
|**PI1.1: The en:ty obtains or**<br>**generates, uses, and**<br>**communicates relevant,**<br>**quality informa:on**<br>**regarding the objec:ves**<br>**related to processing,**<br>**including defini:ons of data**<br>**processed and product and**<br>**service specifica:ons, to**<br>**support the use of products**<br>**and services.**|• Not applicable|• No AWS specific<br>implementa6on|
|**PI1.2: The en:ty implements**<br>**policies and procedures over**<br>**system inputs, including**<br>**controls over completeness**<br>**and accuracy, to result in**<br>**products, services, and**<br>**repor:ng to meet the**<br>**en:ty’s objec:ves.**|• Evaluates processing<br>inputs<br>• Creates and maintains<br>records of system inputs|• To evaluate REST API<br>input, enable Amazon API<br>Gatewayrequest<br>valida6on<br>• To retain system and<br>applica6on logs, enable<br>CloudTrail and export<br>na6ve system and<br>applica6on logs to<br>CloudWatch log groups|





Page 31 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**PI1.3: The en:ty implements**<br>**policies and procedures over**<br>**system processing to result**<br>**in products, services, and**<br>**repor:ng to meet the**<br>**en:ty’s objec:ves.**|• Records systems<br>processing ac6vi6es|• To retain system and<br>applica6on logs, enable<br>CloudTrail and export<br>na6ve system and<br>applica6on logs to<br>CloudWatch log groups|
|---|---|---|
|**PI1.4: The en:ty implements**<br>**policies and procedures to**<br>**make available or deliver**<br>**output completely,**<br>**accurately, and :mely in**<br>**accordance with**<br>**specifica:ons to meet the**<br>**en:ty’s objec:ves.**|• Protects output<br>• Distributes output only to<br>intended par6es<br>• Creates and maintains<br>records of system output|• To protect process<br>output, enable AWS KMS<br>encryp6on on Amazon<br>storage services, such<br>Amazon EBS, Amazon S3,<br>and so on<br>• To limit output<br>distribu6on, implement<br>IAM and IAM Iden6ty<br>Center RBAC and<br>resource access controls<br>• To retain system and<br>applica6on logs, enable<br>CloudTrail and export<br>na6ve system and<br>applica6on logs to<br>CloudWatch log groups|
|**PI1.5: The en:ty implements**<br>**policies and procedures to**<br>**store inputs, items in**<br>**processing, and outputs**<br>**completely, accurately, and**<br>**:mely in accordance with**<br>**system specifica:ons to**<br>**meet the en:ty’s objec:ves.**|• Protects stored items<br>• Archives and protects<br>system records<br>• Creates and maintains<br>records of system storage<br>ac6vi6es|• To protect stored items,<br>enable AWS KMS<br>encryp6on on Amazon<br>storage services, such<br>Amazon EBS, Amazon S3,<br>and so on|





Page 32 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- To protect system records, enable AWS KMS encryp6on on CloudTrail trails and CloudWatch log groups 

- To retain system and applica6on logs, enable CloudTrail and export na6ve system and applica6on logs to CloudWatch log groups 

#### **Non-AWS implemented controls (organiza:onal, process, and people):** 

- Define key characteris6cs of processing inputs for AWS workloads 

- Establish a set of processing specifica6ons for AWS workloads 

## **A series: Availability** 

The _Availability_ criteria in SOC 2 TSC 2017 address the requirement that systems and data be available for opera6on and use as commihed or agreed. These criteria help ensure that the en6ty maintains sufficient capacity, resilience, and disaster recovery to meet service level agreements (SLAs), customer expecta6ons, and opera6onal requirements. 

In AWS-hosted environments, customers can use a range of resilient infrastructure and automa6on services to support availability goals. However, AWS is only responsible for the availability of its global infrastructure and managed services. Customers are responsible for: 

- Architec6ng fault-tolerant workloads 

- Implemen6ng disaster recovery plans 

- Monitoring system health 

- Performing backup and restora6on tes6ng 



Page 33 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**A1.1: The en:ty maintains,**<br>**monitors, and evaluates**<br>**current processing capacity**<br>**and use of system com-**<br>**ponents (infrastructure,**<br>**data, and soZware) to**<br>**manage capacity demand**<br>**and to enable the**<br>**implementa:on of**<br>**addi:onal capacity to help**<br>**meet its objec:ves.**|• Measures current usages<br>• Makes changes based on<br>forecasts|• To manage capacity<br>constraints, enable<br>CloudWatch metrics to<br>monitor resource<br>u6liza6on<br>• To address capacity<br>constraints, configure<br>Auto Scaling for Amazon<br>EC2,Amazon Elas6c<br>Container Service<br>(Amazon ECS), and<br>Amazon Rela6onal<br>Database Service<br>(Amazon RDS)|
|**A1.2: The en:ty authorizes,**<br>**designs, develops or**<br>**acquires, implements,**<br>**operates, approves,**<br>**maintains, and monitors**<br>**environmental protec:ons,**<br>**soZware, data backup**<br>**processes, and recovery**<br>**infrastructure to meet its**<br>**objec:ves.**|• Performs data backup<br>• Implements alternate<br>processing infrastructure|• To protect data from<br>unexpected loss,<br>configure centralized<br>backup policies in AWS<br>Backups for a variety of<br>AWS services, such as<br>Amazon EC2, Amazon<br>EBS, Amazon RDS,<br>Amazon S3, and so on<br>• To limit the impact of<br>loca6on disrup6ons,<br>implement mul6-AZ and<br>mul6-Region<br>architectures in addi6on<br>to cross-Region<br>replica6on|





Page 34 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**A1.3: The en:ty tests**|• Implements business|• To minimize down6me|
|---|---|---|
|**recovery plan procedures**|con6nuity plan tes6ng|and data loss, set up|
|**suppor:ng system recovery**||Elas6c Disaster Recovery|
|**to meet its objec:ves.**||for replica6on and non-<br>disrup6ve tes6ng|



#### **Non-AWS implemented controls (organiza:onal, process, and people):** 

- Define relevant recovery 6me objec6ves (RTOs) and recovery point objec6ves (RPOs) for data and systems based on the BIA of the AWS workloads. 

- Develop system and data backup plans and resilient architecture on AWS using the defined RTOs and RPOs. 

## **C series: Confiden0ality** 

The _ConfidenDality_ criteria in SOC 2 TSC 2017 focus on protec6ng informa6on designated as confiden6al from unauthorized access, use, or disclosure—from crea6on or receipt through storage and final disposal. This includes internal business data, intellectual property, contractual data, and customer-sensi6ve informa6on. 

In AWS environments, while AWS provides secure infrastructure, customers are responsible for managing access to confiden6al data stored or processed in AWS services. This includes iden6fying what data is confiden6al, implemen6ng encryp6on, enforcing access controls, and defining secure data handling and disposal procedures. 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**C1.1: The en:ty iden:fies**<br>**and maintains confiden:al**<br>**informa:on to meet the**<br>**en:ty’s objec:ves related to**<br>**confiden:ality.**|• Iden6fies confiden6al<br>informa6on<br>• Protects confiden6al<br>informa6on from<br>destruc6on|• To iden6fy confiden6al<br>informa6on, enable<br>Macie for sensi6ve data<br>discovery and protec6on<br>• To designate confiden6al<br>informa6on, enforce<br>resource labeling with an<br>Organiza6ons tag policy|





Page 35 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|||• To avoid accidental<br>resource and data<br>dele6on, enable<br>termina6on protec6on<br>on EC2 instances and<br>MFA delete on S3<br>buckets|
|---|---|---|
|**C1.2: The en:ty disposes of**<br>**confiden:al informa:on to**<br>**meet the en:ty’s objec:ves**<br>**related to confiden:ality.**|• Iden6fies confiden6al<br>informa6on for<br>destruc6on<br>• Destroys confiden6al<br>informa6on|• To designate confiden6al<br>informa6on, enforce<br>resource labeling with an<br>Organiza6ons tag policy<br>• To remove expired data<br>automa6cally, apply<br>Amazon S3 Lifecycle<br>configura6on and object<br>expira6on rules to delete<br>old data beyond data<br>reten6on needs|



#### **Non-AWS implemented controls (organiza:onal, process, and people):** 

- Develop a standardized tagging policy for data and resources in AWS 

- Define reten6on requirements for data stored on AWS 

## **P series: Privacy** 

The _Privacy_ criteria in SOC 2 TSC 2017 focus specifically on personal data—how it is collected, used, retained, disclosed, and disposed of in accordance with the en6ty’s privacy commitments and legal requirements. This includes providing proper no6ce, consent, data minimiza6on, user access, breach no6fica6on, and enforcement of privacy policies. 

In AWS environments, while AWS secures the cloud infrastructure, customers are responsible for configuring how personal data is handled within their applica6ons and services, and for enforcing privacy governance aligned with laws like GDPR, HIPAA, or CCPA. 



Page 36 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

### **Relevant AWS services for privacy** 

- **IAM, AWS KMS, and Macie** – for iden6ty-based access, encryp6on, and data classifica6on 

- **CloudTrail and AWS Config** – for audit logging and policy tracking 

- **Macie** – for detec6ng personally iden6fiable informa6on (PII) in Amazon S3 

- **AWS Shield, AWS WAF, and GuardDuty** – for protec6ng personal data from external threats 

- **Lambda and** <u>AWS Step Func6ons</u> – for automated processing and access workflows 

- <u>AWS Control Tower</u> **and SCPs** – for consistent data handling control 

### **P1 series: Privacy Criteria Related to No:ce and Communica:on of Objec:ves Related to Privacy** 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**P1.1: The en:ty provides**<br>**no:ce to data subjects about**<br>**its privacy prac:ces to meet**<br>**the en:ty’s objec:ves**<br>**related to privacy. The no:ce**<br>**is updated and**<br>**communicated to data**<br>**subjects in a :mely manner**<br>**for changes to the en:ty’s**<br>**privacy prac:ces, including**<br>**changes in the use of**<br>**personal informa:on, to**<br>**meet the en:ty’s objec:ves**<br>**related to privacy.**|• Communicates to data<br>subjects<br>• Provides no6ce to data<br>subjects<br>• Covers en66es and<br>ac6vi6es in no6ce|• Host and serve the<br>privacy no6ce using<br>Amazon S3 and<br>CloudFront with version<br>control for accessibility<br>and low latency<br>• Use Amazon Cognitoto<br>link the no6ce<br>acceptance to<br>authen6cated user<br>accounts (for example, on<br>sign-in or registra6on)|





Page 37 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Implement just-in-6me disclosures using API Gateway and Lambda when specific personal data processing is ini6ated (for example, when a file is uploaded or a support 6cket is created) 

- • Send no6fica6on emails using Amazon Simple <u>Email Service (Amazon SES) or push no6fica6ons</u> using Amazon SNS to communicate updates to privacy prac6ces 

- • Use CloudTrail and AWS Config to track backend changes related to systems processing personal data (for example, enabling new logging mechanisms, or adding des6na6ons for personal data) 

- • Use Amazon S3 object versioning, and Amazon <u>Athena and AWS Glue</u> to audit and demonstrate historical privacy no6ce changes 



Page 38 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

#### **Non-AWS implemented controls (organiza:onal, process, and people)** 

- Dram a clear, comprehensive privacy no6ce that outlines what personal data is collected, how it’s used, and with whom it’s shared. 

- Implement a no6ce update procedure that includes legal and compliance review before any privacy-related change is deployed. 

- Define roles responsible for reviewing, upda6ng, and approving privacy no6ces (for example, data privacy officer (DPO), legal counsel, or marke6ng). 

- Make sure that privacy no6ce updates are translated, localized, and accessible to affected users (for example, based on region or language). 

- Maintain a log of no6ce updates, along with date and 6me stamps and internal references to affected systems or processes. 

- Train product teams to no6fy privacy or compliance teams when introducing new data uses that might affect the privacy no6ce. 

### **P2 series: Privacy Criteria Related to Choice and Consent** 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**P2.1: The en:ty**<br>**communicates choices**<br>**available regarding the**<br>**collec:on, use, reten:on,**<br>**disclosure, and disposal of**<br>**personal informa:on to the**<br>**data subjects and the**<br>**consequences, if any, of each**<br>**choice. Explicit consent for**<br>**the collec:on, use,**<br>**reten:on, disclosure, and**<br>**disposal of personal**<br>**informa:on is obtained from**<br>**data subjects or other**<br>**authorized persons, if**<br>**required. Such consent is**<br>**obtained only for the**|• Communicates to data<br>subjects<br>• Communicates<br>consequences of denying<br>or withdrawing consent<br>• Obtains implicit or explicit<br>consent<br>• Documents and obtains<br>consent for new purposes<br>and uses<br>• Obtains explicit consent<br>for sensi6ve informa6on|• Use CloudFront and<br>Amazon S3 to serve<br>privacy preference UIs<br>and policy documents<br>across Regions with low<br>latency<br>• Use AWS WAF to enforce<br>Regional access controls<br>or restrict UI to<br>appropriate users|





Page 39 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**intended purpose of the**<br>**informa:on to meet the**<br>**en:ty’s objec:ves related to**<br>**privacy. The en:ty’s basis for**<br>**determining implicit consent**<br>**for the collec:on, use,**<br>**reten:on, disclosure, and**<br>**disposal of personal**<br>**informa:on is documented.**|• Obtains consent for data<br>transfers|• Use Amazon Cognito to<br>authen6cate users and<br>collect consent as part of<br>sign-up and sign-in flows<br>• Store consent flags and<br>history in Amazon<br>DynamoDB, Amazon<br>Aurora,or Amazon RDS,<br>with 6mestamps,<br>purpose, and method of<br>consent|
|---|---|---|
|||• Use CloudTrail to audit<br>consent-related API<br>ac6ons|
|||• Implement explicit opt-in<br>(for example, for<br>marke6ng) and log opt-<br>outs (for example, cookie<br>rejec6on) using Lambda<br>and API Gateway|
|||• Tag datasets with<br>metadata represen6ng<br>the consent basis using<br>AWS resource tags<br>• Apply IAM or applica6on-<br>level policies that check<br>user consent before data<br>access is granted<br>• No6fy individuals of<br>consequences of consent<br>or denial|





Page 40 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Use Amazon SES or in-app messaging through Amazon SNS to communicate the implica6ons of consent or refusal (for example, account limita6ons) 

- Use Macie to classify PII and map to declared purposes 

- Use CloudWatch Events to trigger remedia6on workflows 

#### **Non-AWS implemented controls (organiza:onal, process, and people)** 

- Maintain a formal consent management policy, defining how, when, and for what purposes consent must be obtained. 

- Make sure that privacy no6ces and interfaces explain individual choices and consequences clearly and understandably. 

- Define and document legal bases for both explicit and implicit consent, aligned with applicable laws (for example, GDPR, and CCPA). 

- Maintain an audit trail for all consent-related interac6ons, including logs of updates, revoca6ons, and user decisions. 

- Train personnel involved in data collec6on (for example, developers, marketers, and support staff) on proper consent capture and use. 

- Implement internal reviews to help ensure that new features or integra6ons respect previously collected consent terms. 

- Establish processes and procedures to revalidate consent periodically, especially for sensi6ve or long-term data reten6on. 



Page 41 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

### **P3 series: Privacy Criteria Related to Collec:on** 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**P3.1: Personal informa:on is**<br>**collected consistent with the**<br>**en:ty’s objec:ves related to**<br>**privacy.**|• Limits the collec6on of<br>personal informa6on<br>• Collects informa6on by<br>fair and lawful means<br>• Collects informa6on from<br>reliable sources<br>• Informs data subjects<br>when addi6onal<br>informa6on is required|• Store and serve declared<br>purposes in your privacy<br>no6ce using Amazon S3<br>and CloudFront<br>• Include purpose<br>metadata (for example,<br>“analy6cs” or “account<br>management”) in data<br>collec6on logic<br>• Tag resources and<br>datasets using AWS<br>resource tags with<br>purpose indicators|
|||• Use IAM condi6on keys to<br>restrict access or write<br>ac6ons based on these<br>tags|
|||• Use CloudTrail and AWS<br>Config to track Lambda,<br>API Gateway, or Amazon<br>S3 write opera6ons and<br>verify alignment with<br>declared collec6on<br>intents|
|||• Use Macie to detect PII in<br>unexpected loca6ons (for<br>example, logs or raw<br>inges6on files)|





Page 42 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Use Security Hub, AWS Config Rules, and CloudWatch alarms to alert if resources are collec6ng or storing personal data outside approved trust zones or paherns 

**P3.2: For informa:on** • Obtains explicit consent **requiring explicit consent,** for sensi6ve informa6on **the en:ty communicates the need for such consent as** • Documents explicit **well as the consequences of** consent to retain **a failure to provide consent** informa6on **for the request for personal informa:on and obtains the consent prior to the collec:on of the informa:on to meet the en:ty’s objec:ves related to privacy** 

- Use Amazon Cognito with pre-signup Lambda triggers to enforce consent capture before user registra6on 

- Integrate consent modals in frontend apps backed by API Gateway and Lambda for processing consent acknowledgments 

- Host privacy no6ces and just-in-6me disclosures using Amazon S3 and CloudFront, possibly integrated into applica6on UIs 

- Use Amazon SNS or Amazon SES to send consent explana6on emails before personal data is collected 



Page 43 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Use DynamoDB, Aurora, or Amazon RDS to persist consent metadata (user ID, 6mestamp, IP, and purpose, consequence no6ce version) 

- • Use CloudTrail to log system-level events indica6ng when and by whom consent was recorded 

- • Use IAM policies or custom logic in Lambda to block workflows that require consent unless the user's consent status is valid and current 

- • Op6onally, enforce consent precondi6ons using Step Func6ons in onboarding workflows 

#### **Non-AWS implemented controls (organiza:onal, process, and people)** 

- Define and document a data collec6on policy outlining allowed purposes, data types, and scope of collec6on. 

- Make sure that all applica6ons and forms limit data fields to only what is necessary for stated objec6ves 

- Conduct privacy impact assessments (PIAs) for new collec6on mechanisms to validate alignment with privacy goals. 

- Review collected data periodically to confirm con6nued relevance to business and privacy objec6ves. 



Page 44 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Train developers and product teams on data minimiza6on principles and purpose alignment. 

- Engage legal and privacy officers to review whether system behavior aligns with declared objec6ves before launch or integra6on. 

- Define a consent management policy with clear procedures for when and how explicit consent is required. 

- Maintain a catalog of processing ac6vi6es that require explicit consent (for example, marke6ng, biometric data, or sensi6ve profiling). 

- Make sure that just-in-6me consent interfaces are part of all user data collec6on touchpoints (web, mobile, or API). 

- Clearly disclose the consequences of not giving consent, such as reduced service availability or limited access. 

- Establish periodic reviews to help ensure legal validity of consent mechanisms, especially for sensi6ve or regulated data types. 

- Train developers and legal teams to collaborate on consent language, 6ming, and user interface placement. 

- Retain consent evidence and link to specific privacy policy version in force at the 6me of acceptance. 

### **P4 series: Privacy Criteria Related to Use, Reten:on, and Disposal** 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**P4.1: The en:ty limits the**<br>**use of personal informa:on**<br>**i**|• Uses personal<br>informa6on for intended|• Define approved<br>purposes and tag data|
|**to the purposes iden:fied in**<br>**the en:ty’s objec:ves**<br>**related to privacy.**|uses|accordingly using AWS<br>resource tags (for<br>example,<br>Purpose=Marke6ng)|





Page 45 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Restrict access by purpose using IAM policies, S3 bucket policies, and <u>AWS Lake Forma6on permissions</u> 

- • Use Macie to scan for PII and confirm that personal data is not being used in non-authorized services or loca6ons 

- • Monitor logs with CloudTrail and CloudWatch to detect unauthorized usage or API calls against PII-linked resources 

- **P4.2 The en:ty retains** • Retains personal • Set Amazon S3 Lifecycle **personal informa:on** informa6on configura6on to delete or **consistent with the en:ty’s** transi6on objects based • Protects personal 

- **objec:ves related to privacy.** on reten6on 6melines informa6on • Use DynamoDB Time to Live (TTL) or database triggers in Aurora or Amazon RDS to purge expired records 

- • Maintain tagging for reten6on dura6on (for example, Reten6on = 90 days) and use AWS Config to validate conformance 



Page 46 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|||• Automate reten6on<br>workflows using Step<br>Func6ons,Amazon<br>EventBridge, and Lambda|
|---|---|---|
|**P4.3: The en:ty securely**<br>**disposes of personal**<br>**informa:on to meet the**<br>**en:ty’s objec:ves related to**<br>**privacy.**|• Captures, iden6fies and<br>flags requests for dele6on<br>• Disposes of, destroys and<br>redacts personal<br>informa6on<br>• Destroys personal<br>informa6on|• Enable Amazon S3 Object<br>Lock with reten6on<br>expira6on followed by<br>dele6on<br>• Use AWS KMS key<br>dele6on schedules to<br>help ensure cryptographic<br>erasure if encryp6on is<br>used<br>• Configure Amazon RDS,<br>Amazon EBS, andAmazon<br>Elas6c File System<br>(Amazon EFS)volumes<br>with secure dele6on<br>protocols before<br>deprovisioning|
|||• Track disposal ac6ons<br>using CloudTrail, and alert<br>on failure events using<br>CloudWatch alarms|
|||• For manual dele6on<br>workflows, build<br>auditable pipelines using<br>Step Func6ons and<br>Lambda to confirm<br>successful erasure of<br>personal data|



#### **Non-AWS implemented controls (organiza:onal, process, and people)** 



Page 47 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

To help ensure personal informa6on is used, retained, and disposed of in line with privacy objec6ves, the organiza6on should consider implemen6ng the following governance and process-level controls: 

- **Data governance policies:** Establish formal policies for data usage, reten6on, and disposal that clearly define approved purposes, 6meframes, and disposal methods aligned with regulatory and contractual obliga6ons. 

- **Data classifica:on and mapping:** Maintain a current data inventory and classifica6on scheme that iden6fies personal data across systems, associates it with intended purposes, and aligns it with defined reten6on schedules. 

- **Reten:on schedules and procedures:** Define reten6on periods by data category and business func6on. Make sure that these are documented, accessible to stakeholders, and regularly reviewed for compliance with evolving legal or business requirements. 

- **Disposal processes and standard opera:ng procedures (SOPs):** Implement secure disposal procedures for personal data, whether manual or automated, including dele6on, anonymiza6on, or destruc6on. Make sure that procedures follow standards like NIST SP 800-88 or local equivalents. 

- **Training and awareness:** Train staff (engineering, support, legal, and so on) on appropriate data handling prac6ces—including restric6ons on data reuse, reten6on obliga6ons, and secure dele6on prac6ces. 

- **Periodic reviews and audits:** Conduct regular reviews to detect data that is outdated, excessive, or improperly retained. Validate that data dele6on workflows operate as intended and audit logs are intact. 

- **Incident response alignment:** Make sure that data handling processes are integrated with breach response and legal hold procedures to help prevent unintended dele6on or misuse during sensi6ve periods. 

### **P5 series: Privacy Criteria Related to Access** 

**Control objec:ve Points of focus covered Customer responsibili:es (SOC 2 TSC 2017) (AWS specific implementa:on)** 



Page 48 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- **P5.1: The en:ty grants** • Authen6cates data • Maintain indexed **iden:fied and authen:cated** subjects’ iden6ty personal informa6on in **data subjects the ability to** queryable stores such as • Permits data subjects 

- **access their stored personal** Amazon RDS, Aurora, or 

- **informa:on for review and,** access to their personal DynamoDB with iden6ty- 

- **upon request, provides** informa6on linked keys 

- **physical or electronic copies of that informa:on to data** • Provides understandable • Create DSAR request 

- **subjects to meet the en:ty’s** personal informa6on forms or portals hosted 

- **objec:ves related to privacy.** within reasonable on Amazon S3 with 

- **If access is denied, data** informa6on **subjects are informed of the** backend APIs in API **denial and reason for such** • Informs data subjects if Gateway and Lambda **denial, as required, to meet** access is denied • Implement secure 

- **the en:ty’s objec:ves related to privacy.** iden6ty verifica6on workflows using Amazon Cognito. 

- • Generate reports using Athena, AWS Glue, or Lambda that compile data into downloadable formats (CSV, PDF) and deliver using Amazon SES or presigned Amazon S3 URLs 

- • Track access events and responses using CloudTrail and log audit entries in CloudWatch Logs 

- **P5.2: The en:ty corrects,** • Communicates denial of • Build secure request **amends, or appends** access requests workflows using API **personal informa:on based** Gateway and Lambda to **on informa:on provided by** allow users to submit **data subjects and** correc6on requests 

- **communicates such** 



Page 49 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- **informa:on to third par:es,** • Permits data subjects to • Store updated data in **as commiPed or required, to** update or correct DynamoDB, Aurora, or **meet the en:ty’s objec:ves** personal informa6on Amazon RDS, with 

- **related to privacy. If a** CloudTrail tracking who 

- **request for correc:on is** • Communicates denial of made changes and when 

- **denied, data subjects are** correc6on requests 

- **informed of the denial and** • Propagate changes using 

- **reason for such denial to** Amazon SNS or 

- **meet the en:ty’s objec:ves** EventBridge to 

- **related to privacy.** downstream systems and third-party APIs 

- • Maintain logs of denied requests and jus6fica6ons using DynamoDB or Amazon S3, and provide user no6fica6ons through Amazon SES or in-app messages 

- • Use IAM policies to restrict edit access to authorized roles and systems only 

#### **Non-AWS implemented controls (organiza:onal, process, and people)** 

To help ensure that data subjects can access and correct their personal informa6on in accordance with privacy objec6ves, the organiza6on should implement the following opera6onal, legal, and governance controls: 

- **Data subject rights and Data subject access requests (DSR and DSAR) procedures:** Establish and document SOPs to handle data subject access and correc6on requests, including iden6fica6on verifica6on, request valida6on, fulfillment 6melines, and escala6on paths. 



Page 50 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- **Iden:ty verifica:on controls:** Implement robust verifica6on methods to confirm the iden6ty of requesters before providing or modifying personal data, in alignment with regional privacy laws (for example, GDPR, CCPA). 

- **Data inventory and mapping:** Maintain a detailed and regularly updated inventory of systems and data flows to enable quick and accurate data retrieval or updates when responding to access or correc6on requests. 

- **Response templates and legal review:** Prepare standardized communica6on templates for gran6ng, denying, or reques6ng clarifica6on on access or correc6on requests. Make sure that legal or privacy teams review complex or denied requests for compliance. 

- **Training and awareness:** Train customer support, legal, engineering, and compliance teams on how to iden6fy, triage, and fulfill data subject rights requests securely and in a 6mely manner. 

- **Denial jus:fica:on and appeals:** Create a policy for handling denied requests, including proper documenta6on of the reason for denial and the process for appeals or complaints. 

- **Change propaga:on:** If personal informa6on is corrected, make sure that downstream systems and third-party processors are no6fied as commihed or required by contract or regula6on. 

- **Logging and monitoring:** Maintain secure logs of all access and correc6on requests and outcomes to support audit readiness and demonstrate accountability. 

### **P6 series: Privacy Criteria Related to Disclosure and No:fica:on** 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**P6.1: The en:ty discloses**<br>**personal informa:on to third**<br>**par:es with the explicit**<br>**consent of data subjects and**<br>**such consent is obtained**<br>**prior to disclosure to meet**<br>**the en:ty’s objec:ves**<br>**related to privacy.**|• Communicates privacy<br>policies to third par6es<br>• Discloses personal<br>informa6on only when<br>appropriate|• Capture disclosure<br>consent through Amazon<br>Cognito or frontend apps<br>powered by API Gateway<br>and Lambda|





Page 51 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

||• Discloses personal<br>informa6on only to<br>appropriate third par6es<br>• Discloses informa6on to<br>third par6es for new<br>purposes|• Record consent status in<br>DynamoDB or Aurora,<br>linked to the third-party<br>service ID<br>• Enforce data sharing logic<br>in backend code to check<br>for valid consent before<br>transferring to external<br>APIs, Amazon S3 cross-<br>account, or PrivateLink<br>endpoints|
|---|---|---|
|||• Use CloudTrail and<br>CloudWatch Logs to<br>monitor disclosure<br>workflows|
|**P6.2: The en:ty creates and**<br>**retains a complete, accurate,**<br>**and :mely record of**<br>**authorized disclosures of**<br>**personal informa:on to**<br>**meet the en:ty’s objec:ves**<br>**related to privacy.**|• Creates and retains<br>records of authorized<br>disclosures|• Log disclosure events in<br>Amazon DynamoDB or<br>Amazon S3 with event<br>metadata (6mestamp,<br>subject ID, recipient, and<br>data shared)<br>• Use EventBridge and Step<br>Func6ons to trigger audit<br>record crea6on upon<br>each authorized sharing<br>• Send audit logs to<br>CloudWatch Logs,<br>Amazon Data Firehose, or<br>Amazon OpenSearch for<br>visualiza6on and tracking|





Page 52 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**P6.3: The en:ty creates and**<br>**retains a complete, accurate,**<br>**and :mely record of**<br>**detected or reported**<br>**unauthorized disclosures**<br>**(including breaches) of**<br>**personal informa:on to**<br>**meet the en:ty’s objec:ves**<br>**related to privacy.**|• Creates and retains<br>records of detected or<br>reported unauthorized<br>disclosures|• Detect breaches using<br>GuardDuty, Security Hub,<br>and Macie (for example,<br>PII exposure in Amazon<br>S3)<br>• Route alerts to Amazon<br>SNS orAmazon Security<br>Lakeand trigger incident<br>logging with Lambda or<br>Step Func6ons<br>• Store incident evidence<br>and breach metadata<br>securely in Amazon S3<br>with AWS KMS<br>encryp6on, using Object<br>Lock to help ensure<br>immutability<br>• Use AWS Audit Manager<br>or third-party investor<br>rela6ons (IR) services to<br>centralize breach<br>inves6ga6on records|
|---|---|---|
|**P6.4: The en:ty obtains**<br>**privacy commitments from**<br>**vendors and other third**<br>**par:es who have access to**<br>**personal informa:on to**<br>**meet the en:ty’s objec:ves**<br>**related to privacy. The en:ty**<br>**assesses those par:es’**<br>**compliance on a periodic**<br>**and as-needed basis and**<br>**takes correc:ve ac:on, if**<br>**necessary.**|• Discloses personal<br>informa6on only to<br>appropriate third par6es<br>• Remediates misuse of<br>personal informa6on by a<br>third party|• Store signed contracts<br>and vendor agreements<br>in Amazon S3 with<br>restricted access using<br>bucket policies<br>• Track vendor onboarding<br>and osoarding and<br>assessment status in<br>DynamoDB or Systems<br>Manager Inventory|





Page 53 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Use <u>AWS Ar6fact</u> to request and track thirdparty privacy cer6fica6ons (for example, ISO 27701, SOC 2 reports) 

- Maintain an internal vendor privacy risk register in Amazon RDS or integrate with governance, risk, and compliance (GRC) services (for example, ServiceNow) 

**P6.5: The en:ty obtains** • Remediates misuse of **commitments from vendors** personal informa6on by a **and other third par:es with** third party **access to personal informa:on to no:fy the** • Reports actual or **en:ty in the event of actual** suspected unauthorized **or suspected unauthorized** disclosures **disclosures of personal informa:on. Such no:fica:ons are reported to appropriate personnel and acted on in accordance with established incidentresponse procedures to meet the en:ty’s objec:ves related to privacy.** 

- Include breach no6fica6on clauses in third-party contracts and track compliance in your contract database 

- Set up Amazon SNS or custom Lambda endpoints to receive breach alerts from vendors or integrated systems 

- Integrate with third-party services using EventBridge or API Gateway for automated intake of vendor incident no6fica6ons 



Page 54 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|||• Route alerts to Security<br>Hub or ChatOps channels<br>(for example, Amazon<br>Chime or Slack) for<br>immediate response|
|---|---|---|
|**P6.6: The en:ty provides**<br>**no:fica:on of breaches and**<br>**incidents to affected data**<br>**subjects, regulators, and**<br>**others to meet the en:ty’s**<br>**objec:ves related to privacy.**|• Remediates misuse of<br>personal informa6on by a<br>third party<br>• Provides no6ce of<br>breaches and incidents|• Use Security Hub and<br>GuardDuty to detect<br>suspicious ac6vity that<br>might indicate data<br>misuse or a breach<br>• Aggregate findings into<br>centralized response<br>workflows using Amazon<br>Detec6ve,EventBridge,<br>and Lambda to triage and<br>route incidents|
|||• Store detailed forensic<br>logs and analysis in<br>Amazon S3 (with<br>versioning and AWS KMS<br>encryp6on) and<br>CloudTrail Lake for long-<br>term querying|
|||• Maintain automated<br>alerts and escala6ons<br>using Amazon SNS and<br>integrate with incident<br>6cke6ng systems through<br>Lambda or Step Func6ons|





Page 55 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

   - Use Macie to detect if exposed or exfiltrated data contains PII or personal health informa6on (PHI) and tag those objects for breach scope es6ma6on 

- Create no6fica6on templates and dispatch alerts to affected users using Amazon SES or Amazon SMS through <u>Amazon Pinpoint</u> 

- **P6.7: The en:ty provides** • Iden6fies types of • **data subjects with an** personal informa6on and **accoun:ng of the personal** handling process • Iden6fies types of **informa:on held and** personal and sensi6ve **disclosure of the data** • Captures, iden6fies, and informa6on and how **subjects’ personal** communicates requests they’re handled 

- **informa:on, upon the data** for informa6on **subjects’ request, to meet** • Captures and responds to **the en:ty’s objec:ves** data subject requests for 

- **related to privacy.** accoun6ng of personal data and disclosures 

- • Iden6fy personal or sensi6ve data types using Macie to scan Amazon S3 buckets for PII, financial, and health data; classify and label assets based on sensi6vity 



Page 56 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Use <u>AWS Glue Data Catalog</u> to maintain metadata on datasets containing personal informa6on, including their source, transforma6on logic, and des6na6ons 

- • Use CloudTrail Lake to query detailed logs about data access and disclosures by IAM users, roles, or services 

- • Capture data subject requests through API Gateway and Lambda, storing request logs and 6mestamps in DynamoDB or Amazon RDS 

- • Securely generate and share accoun6ng reports using Amazon S3 (with S3 Object Lock and AWS KMS encryp6on) and no6fy users using Amazon SES 

- • Use Amazon Cognito for secure authen6ca6on and iden6ty linkage of data requests to specific data subjects 



Page 57 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Implement centralized evidence gathering using Audit Manager and Athena for structured querying across logs, systems, and data repositories 

- Integrate 6cke6ng or workflow systems using Step Func6ons and EventBridge for request status tracking and escala6on 

#### **Non-AWS implemented controls (organiza:onal, process, and people)** 

- Define and enforce a third-party data sharing policy, including requirements for explicit consent prior to disclosure. 

- Maintain data processing agreements (DPAs) with all vendors accessing personal data, with clauses on use, breach no6fica6on, and termina6on handling. 

- Establish a consent management process to capture, store, and retrieve data subject authoriza6ons for disclosures. 

- Maintain a disclosure log documen6ng all authorized and unauthorized data sharing events, including purpose, recipient, and lawful basis. 

- Implement a privacy incident response plan, covering breach detec6on, classifica6on, communica6on 6melines, and regulator no6fica6on procedures. 

- Define and document vendor breach repor6ng obliga6ons and integrate vendor disclosures into internal response workflows. 

- Conduct periodic vendor privacy risk assessments and follow up on non-compliance with correc6ve ac6on. 

- Respond to data subject access and accoun6ng requests with verified iden6ty procedures and structured reports of held and disclosed informa6on. 



Page 58 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Provide training and awareness for legal, compliance, IT, and procurement teams on privacy obliga6ons 6ed to disclosure, breach response, and vendor oversight. 

- Maintain documenta6on and audit readiness for all privacy-related decisions, processes, and excep6ons related to third-party data disclosures. 

### **P7 series: Privacy Criteria Related to Quality** 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**P7.1: The en:ty collects and**<br>**maintains accurate, up-to-**<br>**date, complete, and relevant**<br>**personal informa:on to**<br>**meet the en:ty’s objec:ves**<br>**related to privacy.**|• Helps ensure accuracy<br>and completeness of<br>personal informa6on<br>• Helps ensure relevance of<br>personal informa6on|• Implement data<br>valida6on and cleansing<br>rou6nes at data inges6on<br>points using Lambda,<br>AWS Glue, orAWS Glue<br>DataBrew to enforce<br>accuracy and format rules|
|||• Use Data Catalog to<br>maintain metadata<br>describing the source,<br>context, and use case of<br>personal data, suppor6ng<br>data relevance<br>assessments|





Page 59 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Apply Macie to classify and review data stored in Amazon S3, flagging sensi6ve data stored in non-relevant loca6ons. Integrate Amazon RDS, DynamoDB, or Amazon with business logic that enforces required fields and input constraints for personal informa6on 

- • Use <u>Amazon AppFlow or AWS Database Migra6on Service (AWS DMS)to</u> synchronize personal data across systems to reduce inconsistencies and duplica6on. 

- • Use CloudWatch and AWS Config to monitor configura6on drim in systems managing personal data. 

#### **Non-AWS implemented controls (organiza:onal, process, and people)** 

- Define policies and procedures to help ensure that personal data is collected only if relevant and with a clearly documented lawful purpose. 

- Train staff on how to validate and update data during collec6on and throughout the data lifecycle. 

- Implement periodic reviews and quality audits of personal data to detect and correct inaccuracies or outdated entries. 



Page 60 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Establish data stewardship roles responsible for maintaining the accuracy, completeness, and relevance of personal informa6on. 

- Enable data subject access and correc6on workflows to help ensure that individuals can update their own informa6on when necessary. 

- Limit collec6on forms and field to what is essen6al for the declared purpose, avoiding overcollec6on of personal data. 

### **P8 series: Privacy Criteria Related to Monitoring and Enforcement** 

|**SOC 2 TSC iden:fier**|**Points of focus covered**|**Customer responsibili:es**<br>**(AWS specific**<br>**implementa:on)**|
|---|---|---|
|**P8.1: The en:ty implements**<br>**a process for receiving,**<br>**addressing, resolving, and**<br>**communica:ng the**<br>**resolu:on of inquiries,**<br>**complaints, and disputes**<br>**from data subjects and**<br>**others and periodically**<br>**monitors compliance to**<br>**meet the en:ty’s objec:ves**<br>**related to privacy.**<br>**Correc:ons and other**<br>**necessary ac:ons related to**<br>**iden:fied deficiencies are**<br>**made or taken in a :mely**<br>**manner.**|• Communicates to data<br>subjects<br>• Addresses inquiries,<br>complaints, and disputes<br>• Documents and<br>communicates dispute<br>resolu6on and recourse<br>• Documents and reports<br>compliance review<br>results<br>• Documents and reports<br>instances of<br>noncompliance<br>• Performs ongoing<br>monitoring|• Use API Gateway and<br>Lambda to build secure<br>inquiry intake endpoints<br>and integrate with case<br>management tools<br>• Store and track inquiry<br>metadata using<br>DynamoDB or Amazon<br>RDS, including<br>6mestamps, resolu6on<br>steps, and outcomes<br>• Use Amazon SES or<br>Pinpoint for secure<br>no6fica6on to data<br>subjects confirming<br>receipt and resolu6on of<br>complaints|





Page 61 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|• Implement compliance|
|---|
|dashboards using<br>Amazon QuickSight,<br>Athena, and Amazon S3<br>to visualize dispute<br>resolu6on SLAs,<br>paherns, and<br>noncompliance trends|
|• Use AWS Config and|
|Security Hub to monitor<br>compliance across AWS<br>resources; generate<br>alerts on configura6on<br>viola6ons 6ed to privacy<br>controls|
|• Maintain immutable logs|
|using CloudTrail and|
|Amazon S3 Object Lock|
|for audit support|



#### **Non-AWS implemented controls (organiza:onal, process, and people)** 

- Establish a formal complaint-handling policy with defined intake channels (for example, web, phone, or email) and 6melines for response and resolu6on. 

- Train customer service, privacy, and legal teams to handle privacy inquiries and resolve complaints in accordance with applicable laws (for example, CCPA, or GDPR). 

- Document every inquiry or complaint, track resolu6on steps, and provide wrihen confirma6on to the individual regarding the outcome. 

- Perform periodic privacy compliance reviews and generate internal reports for leadership, outlining any issues, trends, and improvement ac6ons. 

- Track and report instances of noncompliance, applying correc6ve or disciplinary ac6ons as appropriate. 



Page 62 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

- Maintain an ongoing monitoring plan that assesses the effec6veness of controls, remediates deficiencies, and helps ensure con6nuous improvement. 

- Review and update processes regularly to incorporate regulatory changes and lessons learned from past complaints or incidents. 

**Note** : For detailed implementa6on guidance and service selec6on, see the AWS Privacy <u>Reference Architecture. It provides detailed paherns and AWS service recommenda6ons to help</u> build privacy-aware systems aligned with SOC 2 and other privacy frameworks. 

# Control design and documenta#on best prac#ces 

Mee6ng SOC 2 requirements in AWS is not just about implemen6ng technical features—it’s about designing and documen6ng well-governed controls that align with both AICPA's expecta6ons and your opera6ng model. 

## **Efficient SOC 2 control** 

Each control should include the following key ahributes to help ensure alignment with SOC 2 compliance expecta6ons: 

- **Purpose:** Aligned to a specific Trust Services Criterion 

- **Owned:** Assigned to a responsible individual or team 

- **Recurring:** Executed at a defined cadence 

- **Evidence:** Producing auditable proof of opera6on 

- **Mapped (where applicable):** Linked to AWS configura6ons, service sevngs, or organiza6on policies that support the control’s intent; not all controls will map directly to AWS features. 

## **Documen0ng controls in AWS environments** 

AWS controls must be supplemented with organiza6onal governance. Each documented control should include: 

|**A"ribute**|**Descrip.on**|
|---|---|
|**Control ID**|A unique label +ed to a Trust Service Criterion (for example, CC6.1-MFA)|





Page 63 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**A"ribute**|**Descrip.on**|
|---|---|
|**Control descrip.on**|What the control does and why it exists|
|**Owner**|Responsible person or team|
|**Execu.on frequency**|Daily, weekly, monthly, or quarterly|
|**AWS services involve**d|For example, IAM, AWS KMS, AWS Config, CloudTrail|
|**Expected evidence**|For example, policy documents, logs, screenshots, and Config reports|
|**Points of focus addressed**|Which points of focus are sa+sfied by this control|



# Evidence collec#on and audit readiness 

A successful SOC 2 audit relies on 6mely, accurate, and consistent evidence that demonstrates how controls are opera6ng over 6me. For customer-managed controls that use AWS services in their design and opera6on, AWS provides several tools—such as CloudTrail, AWS Config, Security Hub, and Audit Manager—to help simplify evidence collec6on. However, customers must s6ll design and maintain a structured process to manage this evidence in a traceable and auditable manner. 

**Note:** Audit evidence sources are not limited to AWS services; they can also include internal policy documents, IT 6cke6ng systems, access reviews, screenshots, third-party logs, and other manual procedures, depending on the nature of the control 

## **AWS sources of evidence** 

The following table outlines common AWS services used as sources of evidence during audits, along with the type of informa6on each provides. 

|**AWS tool**|**Type of evidence**|
|---|---|
|**CloudTrail**|API calls, authen+ca+on, config changes|
|**AWS Config**|Compliance evalua+ons, resource history|
|**CloudWatch Logs**|Applica+on logs, alarms, usage data|
|**IAM Reports**|User and group access rights and changes|





Page 64 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

|**AWS tool**|**Type of evidence**|
|---|---|
|**Audit Manager**|Control framework mapping, evidence folders|
|**Security Hub**|Findings, status of integrated services|



## **Evidence collec0on strategies** 

To support audit readiness and demonstrate control effec6veness, the following evidence collec6on strategies can be implemented as part of your compliance program. 

- Tag ar6facts with control IDs (for example, CC5.3, or A1.2) 

- Use Amazon S3 with versioning and access logs for long-term evidence reten6on 

- Automate evidence exports with EventBridge and Lambda (for example, send logs to Amazon S3) 

- Prepare walk-Polthroughs describing how each control works and where evidence is stored 

- Run mock audits using Audit Manager or internal security teams to simulate ques6ons and evidence requirements 

# Risk and governance: SOC 2 for the execu#ve team 

It is important for responsible execu6ves to understand that the AICPA TSC that are assessed during the SOC 2 audit are equally focused on governance and specific technical or security measures such as firewalls, encryp6on, or log management and analysis. Your customers request SOC 2 reports from service providers such as your company to understand the risks presented to their own organiza6on as they use the services provided by you, the service provider organiza6on. The SOC 2 auditor’s opinion will rest on how well your organiza6on iden6fies and responds to the risks inherent in your opera6onal environment to effec6vely and securely serve your customers. 

This is a cri6cal part of the SOC 2 assessment that many execu6ve teams don’t an6cipate, and it can be cri6cal to the outcome of your audit. The SOC 2 auditor will be trying to understand the rela6onship between management and any informa6on security-related business processes or func6ons; therefore, the execu6ve team should be able to demonstrate the free flow and 



Page 65 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

frequent considera6on of informa6on and metrics regarding exis6ng risks and the measures adopted by the organiza6on to mi6gate or manage those risks. 

Basic principles associated with the management of IT risk: 

- Business leaders are expected to invest money for one of two reasons: either to exploit opportuni6es or to mi6gate risks. In every business, financial resources (always limited) must be directed as efficiently as possible. This includes resources dedicated to the mi6ga6on of IT risk. 

- The existence of specific IT-related risks is why businesses create informa6on security programs. 

- Like all risks to the enterprise, IT-related risk must be managed and monitored. This is normally accomplished using a _risk register_ that should roll up into the overall corporate risk management program, which is frequently managed by the CFO or Legal teams. 

- The financial decisions associated with IT risk management should be balanced along with the remainder of the risks managed by the organiza6on’s execu6ve team. For this to happen, execu6ves should maintain awareness of current risks and poten6al impacts, so that appropriate resources can be assigned. 

During the SOC 2 audit, the auditor will seek to answer the following ques6ons: 

- Does the Board of Directors (or Execu6ve team) understand the level of risk for the organiza6on based upon accurate informa6on received from the individual business units or departments? 

- Does the Board of Directors or execu6ve team act to address the risk at the appropriate level and in a sufficient manner? 

The SOC 2 audit is an assessment of the level of posi6ve control the board of directors or the execu6ve team exerts over the assessment and understanding of risks to the services being provided to their customers, the organiza6onal systems and controls they put in place to make sure that those risks are addressed and managed appropriately, and the con6nued monitoring and 6mely management of evolving risks to the organiza6on. 

To explain all the specific func6ons of an effec6ve IT risk management program is beyond the scope of this whitepaper. See the earlier sec6on, _CC9 series: Risk MiDgaDon_ , for more specific informa6on regarding the Risk Management TSC. While the specific technical measures and solu6ons outlined in this document are essen6al for exer6ng control over your AWS-located 



Page 66 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

workloads, they aren’t sufficient by themselves; service providers must demonstrate an appropriate level of ahen6on to all iden6fied sources of risk to the delivery of services to their customers. 

# Conclusion and recommenda#ons 

The SOC2 framework is not meant to be a point-in-6me checkbox exercise, it is an ongoing trust framework. Organiza6ons opera6ng in AWS must go beyond security features and demonstrate governance, consistency, and maturity in how they implement and maintain controls. 

This whitepaper serves as a guide for security architects, compliance leaders, DevOps teams, and assessors to: 

- Understand SOC 2 requirements in AWS-specific terms 

- Implement controls that address both technical and procedural gaps 

- Automate evidence collec6on using AWS-na6ve tooling 

- Sustain compliance with minimal opera6onal burden 

## **Key takeaways** 

- Use the AWS Shared Responsibility Model to scope your control obliga6ons clearly. 

- Use AWS services (such as IAM, AWS Config, CloudTrail, AWS KMS, and AWS Backup) for control enforcement and evidence genera6on. 

- Build and maintain a control register with traceable mappings to TSC and points of focus. 

- Prepare for audits con6nuously by trea6ng SOC 2 as a living part of your cloud opera6ng model. 

# Contributors 

Contributors to this document include: 

- Abdul Javid, Sr. Assurance Consultant, AWS Security Assurance Services LLC 

- Viktor Mu, Sr. Assurance Consultant, AWS Security Assurance Service LLC 

- Wil Woodrum, Sr. Assurance Consultant, AWS Security Assurance Services LLC 



Page 67 

_SOC 2 - Guidance, advisory for AWS customers_ 

_Amazon Web Services_ 

# Further reading 

For addi6onal informa6on, see: 

- <u>System and Organiza6on Controls: SOC Suite of Services</u> 

- <u>Trust Services Criteria 2017</u> 

- <u>AWS prescrip6ve guidance</u> 

- <u>AWS SOC Reports FAQ</u> 

- <u>AWS Whitepapers &</u> guides 

- <u>NIST Risk Management Framework</u> 

# Document revisions 

|**Date**|**Descrip.on**|
|---|---|
|**July 21, 2025**|Ini+al version|





Page 68 

