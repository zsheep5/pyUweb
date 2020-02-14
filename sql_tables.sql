CREATE TABLE public.sec_access
(
    sa_id serial,
    sa_allowed boolean,
    sa_target_id integer,
    sa_target_type character(10) COLLATE pg_catalog."default" DEFAULT 'user'::bpchar,
    sa_app_name character(50) COLLATE pg_catalog."default",
    sa_app_function character(50) COLLATE pg_catalog."default",
    CONSTRAINT sec_access_pkey PRIMARY KEY (sa_id)
        USING INDEX TABLESPACE magwerks
);
CREATE TABLE public.sec_groups
(
    sg_id serial,
    sg_name character(50) COLLATE pg_catalog."default",
    sg_descrip character(100) COLLATE pg_catalog."default",
    sg_members integer[],
    CONSTRAINT sec_groups_pkey PRIMARY KEY (sg_id)
        USING INDEX TABLESPACE magwerks
);
CREATE TABLE public.client_state
(
    cs_id serial,
    cs_data json,
    cs_user_id integer DEFAULT '-1'::integer,
    cs_ip inet DEFAULT '0.0.0.0'::inet,
    CONSTRAINT client_state_pkey PRIMARY KEY (cs_id)
        USING INDEX TABLESPACE magwerks
);
CREATE TABLE public.csb
(
    csb_id character(256) COLLATE pg_catalog."default" NOT NULL,
    csb_expires timestamp without time zone,
    CONSTRAINT csb_pkey PRIMARY KEY (csb_id)
        USING INDEX TABLESPACE magwerks
);

CREATE TABLE public.users
(
    user_id serial,
    user_name character(32) COLLATE pg_catalog."default",
    user_last character(32) COLLATE pg_catalog."default",
    user_email character(80) COLLATE pg_catalog."default",
    user_type character(10) COLLATE pg_catalog."default",
    user_pwd text COLLATE pg_catalog."default",
    user_grp integer,
    user_displayname character(32) COLLATE pg_catalog."default",
    user_avatar character(80) COLLATE pg_catalog."default",
    CONSTRAINT users_pkey PRIMARY KEY (user_id)
        USING INDEX TABLESPACE magwerks
);

CREATE OR REPLACE FUNCTION mcal.create_cert(pcalprohd_id integer)
    RETURNS integer LANGUAGE 'plpgsql' COST 100  VOLATILE 
AS $BODY$

DECLARE
	newid integer = nextval('mcal.calhead_calhead_id_seq');	
	
BEGIN
    
	 insert into mcal.calhead (calhead_id, calhead_calprohd_id, calhead_caldate, calhead_eqname) 
	 	select (newid, pcalprohd_id, now()::date,  (now()::date + interval '6 month')::date
				from calprohd
				where clalprohd_id =pcalprohd_id ;

	 insert into mcal.caldetail (caldetail_calhead_id, caldetail_calprorules_id, caldetails_seqence, 
			caldetail_datatype, caldetail_descrip_text_datacollect, caldetail_default_text, 
			caldetail_checkoff_descrip, caldetail_checkoff_values, caldetail_devtext) 
		select newid, calprorules_id, calprorules_seqence, calprorules_datatype, 
				calprorules_textdata_descrip, calprorules_textdata_default, 
				calprorules_checkoff_descrip, calprorules_checkoff_values, 
				calprorules_devtext 
			from mcal.calprorules where 
				calprorules_calprohd_id =  pcalprohd_id
			order by calprorules_seqence asc 
			on conflict (caldetail_calhead_id, caldetails_seqence, caldetail_calprorules_id) do nothing;

	return newid;
end;
$BODY$;

CREATE OR REPLACE FUNCTION mcal.set_cert_header(pcalhead_id integer, psales_number integer)
RETURNS integer LANGUAGE 'plpgsql' COST 100  VOLATILE 
AS $BODY$

	DECLARE
	_r record;
	
BEGIN
	Select cohead_cust_id, 
		cohead_custponumber,
		cohead_shiptoname,
		cohead_shiptoaddress1,
		cohead_shiptoaddress2,
		cohead_shiptoaddress3,
		cohead_shiptoaddress4,
		cohead_shiptoaddress5,
		cohead_shiptocity,
    	cohead_shiptostate,
    	cohead_shiptozipcode,
		cohead_shiptocountry,
		cohead_shipto_cntct_id,
		cohead_shipto_cntct_honorific,
		cohead_shipto_cntct_first_name,
		cohead_shipto_cntct_last_name,
		cohead_shipto_cntct_phone,
		cohead_shipto_cntct_title,
		cohead_shipto_cntct_fax,
		cohead_shipto_cntct_email
		into _r 
		from cohead 
		where cohead_number = psales_number::text;
	
	update mcal.calhead set 
		calhead_cust_id = _r.cohead_cust_id,
		calhead_cntct_id = _r.cohead_shipto_cntct_id,
		calhead_addr_line1 = _r.cohead_shiptoaddress1 ,
		calhead_addr_line2 = _r.cohead_shiptoaddress2,
		calhead_addr_line3 = _r.cohead_shiptoaddress3,
		calhead_addr_city = _r.cohead_shiptocity ,
		calhead_addr_state = _r.cohead_shiptostate,
		calhead_addr_postalcode = _r.cohead_shiptozipcode,
		calhead_addr_country = _r.cohead_shiptocountry ,

		calhead_cntct_name = _r.cohead_shipto_cntct_first_name || ' ' || _r.cohead_shipto_cntct_last_name ,
		calhead_cntct_phone = _r.cohead_shipto_cntct_phone,
		calhead_cntct_fax = _r.cohead_shipto_cntct_fax,
		calhead_cntct_email = _r.cohead_shipto_cntct_email ,
		calhead_cntct_title = _r.cohead_shipto_cntct_title,

		calhead_cust_po = _r.cohead_custponumber
				
end;
$BODY$