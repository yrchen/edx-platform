define([
    'jquery',
    'common/js/spec_helpers/ajax_helpers',
    'support/js/views/certificates'
], function($, AjaxHelpers, CertificatesView) {
    'use strict';

    describe('CertificatesView', function() {

        var view = null;

        var SEARCH_RESULTS = [
            {
                "username": "student",
                "status": "notpassing",
                "created": "2015-08-05T17:32:25+00:00",
                "grade": "0.0",
                "type": "honor",
                "course_key": "course-v1:edX+DemoX+Demo_Course",
                "download_url": null,
                "modified": "2015-08-06T19:47:07+00:00"
            },
            {
                "username": "student",
                "status": "downloadable",
                "created": "2015-08-05T17:53:33+00:00",
                "grade": "1.0",
                "type": "verified",
                "course_key": "edx/test/2015",
                "download_url": "http://www.example.com/certificate.pdf",
                "modified": "2015-08-06T19:47:05+00:00"
            },
        ];

        var searchFor = function(query, requests, response) {
            var results = [];

            // Enter the search term and submit
            view.setUserQuery(query);
            view.triggerSearch();

            // Simulate a response from the server
            AjaxHelpers.expectJsonRequest(requests, "GET", "/certificates/search?query=student@example.com");
            AjaxHelpers.respondWithJson(requests, response);

            // Retrieve the results from the DOM
            $(".certificates-results tr").each(function(rowIndex, rowValue) {
                var columns = [];
                $(rowValue).children("td").each(function(colIndex, colValue) {
                    columns[colIndex] = $(colValue).html();
                });

                if (columns.length > 0) {
                    results.push(columns);
                }
            });

            return results;
        };

        beforeEach(function () {
            setFixtures('<div class="certificates-content"></div>');
            view = new CertificatesView({
                el: $('.certificates-content')
            }).render();
        });

        it('renders itself', function() {
            expect($(".certificates-search").length).toEqual(1);
            expect($(".certificates-results").length).toEqual(1);
        });

        it('searches for certificates and displays results', function() {
            var requests = AjaxHelpers.requests(this),
                results = searchFor("student@example.com", requests, SEARCH_RESULTS);

            // Expect that the results displayed on the page match the results
            // returned by the server.
            expect(results.length).toEqual(SEARCH_RESULTS.length);

            // Check the first row of results
            expect(results[0][0]).toEqual(SEARCH_RESULTS[0].course_key);
            expect(results[0][1]).toEqual(SEARCH_RESULTS[0].type);
            expect(results[0][2]).toEqual(SEARCH_RESULTS[0].status);
            expect(results[0][3]).toContain("Not available");
            expect(results[0][4]).toEqual(SEARCH_RESULTS[0].grade);
            expect(results[0][5]).toEqual(SEARCH_RESULTS[0].modified);

            // Check the second row of results
            expect(results[1][0]).toEqual(SEARCH_RESULTS[1].course_key);
            expect(results[1][1]).toEqual(SEARCH_RESULTS[1].type);
            expect(results[1][2]).toEqual(SEARCH_RESULTS[1].status);
            expect(results[1][3]).toContain(SEARCH_RESULTS[1].download_url);
            expect(results[1][4]).toEqual(SEARCH_RESULTS[1].grade);
            expect(results[1][5]).toEqual(SEARCH_RESULTS[1].modified);
        });

        it('searches for certificates and displays a message when there are no results', function() {
            expect(1).toBe(2);
        });

        it('automatically searches for an initial query if one is provided', function() {
            expect(1).toBe(2);
        });

        it('regenerates a certificate for a student', function() {
            expect(1).toBe(2);
        });

        it('displays an error when a search cannot be performed', function() {
            expect(1).toBe(2);
        });
    });
});
