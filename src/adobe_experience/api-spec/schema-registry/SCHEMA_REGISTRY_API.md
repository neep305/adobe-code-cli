Use the Schema Registry API to access the Schema Library within Adobe Experience Platform. The registry provides a user interface and RESTful API from which all available library resources are accessible. Programmatically manage all schemas and related Experience Data Model (XDM) resources available to you within Platform. This includes those defined by Adobe, Experience Platform partners, and vendors whose applications you use.

- Related documentation:
    - [XDM documentation](http://www.adobe.com/go/xdm-home-en)
- Visualize API calls with Postman (a free, third-party software):
    - [Schema Registry API Postman collection on GitHub](https://github.com/adobe/experience-platform-postman-samples/blob/master/apis/experience-platform/Schema%20Registry%20API.postman_collection.json)
    - [Video guide for creating the Postman environment](https://video.tv.adobe.com/v/28832)
    - [Steps for importing environments and collections in Postman](https://learning.getpostman.com/docs/postman/collection_runs/using_environments_in_collection_runs/)
- API paths:
    - PLATFORM Gateway URL: https://platform.adobe.io
    - Base path for this API: /data/foundation/schemaregistry
    - Example of a complete path for making a call to "/stats":             https://platform.adobe.io/data/foundation/schemaregistry/stats

- Required headers:
    - All calls require the headers Authorization, x-gw-ims-org-id, and x-api-key. For more information on how to obtain these values, see the [authentication tutorial](http://www.adobe.com/go/platform-api-authentication-en).
    - All resources in Experience Platform are isolated to specific virtual sandboxes. All requests to Platform APIs require the header x-sandbox-name whose value is the all-lowercase name of the sandbox the operation will take place in (for example, "prod"). See the [sandboxes overview](https://adobe.com/go/sandbox-overview-en) for more information.
    - All GET requests to the Schema Registry require an Accept header to determine what data is returned by the system. See the [section on](https://experienceleague.adobe.com/docs/experience-platform/xdm/api/getting-started.html?lang=en#accept) Accept [headers](https://experienceleague.adobe.com/docs/experience-platform/xdm/api/getting-started.html?lang=en#accept) in the Schema Registry developer guide for more information.
    - All requests with a payload in the request body (such as POST, PUT, and PATCH calls) must include the header Content-Type with a value of application/json.
- API error handling:
    - Refer to the Experience Platform API troubleshooting guide for [FAQs](https://experienceleague.adobe.com/docs/experience-platform/landing/troubleshooting.html#faq), [API status codes](https://experienceleague.adobe.com/docs/experience-platform/landing/troubleshooting.html#api-status-codes), and [request header errors](https://experienceleague.adobe.com/docs/experience-platform/landing/troubleshooting.html#request-header-errors).